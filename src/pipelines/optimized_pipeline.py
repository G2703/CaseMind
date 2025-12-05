"""
Optimized Ingestion Pipeline for CaseMind.
Async architecture with parallel processing, rate limiting, and batching.
"""

import asyncio
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime
import json

from src.core.config import Config
from src.core.lifecycle import LifecycleManager
from src.pipelines.stages import (
    PDFStage,
    ExtractionStage,
    EmbeddingStage,
    IngestionStage,
    HaystackWrapperStage,
)

logger = logging.getLogger(__name__)


@dataclass
class PipelineResult:
    """Overall pipeline result."""
    total_files: int
    successful: int
    failed: int
    skipped: int
    duration_seconds: float
    results: List[Dict[str, Any]]
    failed_files: List[Dict[str, Any]]


class OptimizedPipeline:
    """
    Optimized ingestion pipeline with async processing.
    
    Architecture:
        1. PDF Stage: Parallel PDF→Markdown (3 workers)
        2. Extraction Stage: Rate-limited LLM extraction (sequential, 3 RPM)
        3. Embedding Stage: Batched embedding generation (optimized batching)
        4. Ingestion Stage: Batched Weaviate writes
    
    Features:
        - Lifecycle management (startup/shutdown)
        - Progress monitoring
        - Error handling with retry
        - Failed files tracking
    """
    
    def __init__(self, config: Optional[Config] = None, skip_existing: bool = True):
        """
        Initialize optimized pipeline.
        
        Args:
            config: Configuration instance
            skip_existing: Skip files already in Weaviate
        """
        self.config = config or Config()
        self.skip_existing = skip_existing
        
        # Lifecycle manager
        self.lifecycle_manager: Optional[LifecycleManager] = None
        
        # Pipeline stages
        self.pdf_stage: Optional[PDFStage] = None
        self.extraction_stage: Optional[ExtractionStage] = None
        self.embedding_stage: Optional[EmbeddingStage] = None
        self.ingestion_stage: Optional[IngestionStage] = None
        self.haystack_wrapper: Optional[HaystackWrapperStage] = None
        
        # Progress tracking
        self.progress_callback: Optional[callable] = None
        
        # Results tracking
        self.failed_files: List[Dict[str, Any]] = []
        
        logger.info("OptimizedPipeline created")
    
    async def initialize(self) -> bool:
        """
        Initialize pipeline and all resources.
        
        Returns:
            True if successful, False otherwise
        """
        logger.info("=" * 70)
        logger.info("Initializing Optimized Pipeline...")
        logger.info("=" * 70)
        
        try:
            # Initialize lifecycle manager (starts all resources)
            self.lifecycle_manager = LifecycleManager(config=self.config)
            success = await self.lifecycle_manager.startup()
            
            if not success:
                logger.error("Lifecycle manager startup failed")
                return False
            
            # Initialize pipeline stages
            logger.info("\nInitializing pipeline stages...")
            
            # PDF Stage (with duplicate detection)
            self.pdf_stage = PDFStage(
                num_workers=self.config.max_workers,
                weaviate_pool=self.lifecycle_manager.weaviate_pool,
                skip_existing=self.skip_existing
            )
            
            # Initialize Haystack wrapper (runs extraction+embedding as one stage)
            self.haystack_wrapper = HaystackWrapperStage(config=self.config)
            await self.haystack_wrapper.initialize(
                self.lifecycle_manager.openai_pool,
                self.lifecycle_manager.embedding_pool,
            )
            
            # Embedding Stage is managed by the Haystack wrapper; keep attribute for compatibility
            self.embedding_stage = None
            
            # Ingestion Stage
            self.ingestion_stage = IngestionStage(
                skip_existing=self.skip_existing,
                config=self.config
            )
            await self.ingestion_stage.initialize(self.lifecycle_manager.weaviate_pool)
            
            logger.info("✓ All pipeline stages initialized")
            
            return True
            
        except Exception as e:
            logger.error(f"Pipeline initialization failed: {e}", exc_info=True)
            return False
    
    async def shutdown(self) -> None:
        """Gracefully shutdown pipeline and resources."""
        logger.info("\nShutting down pipeline...")
        
        if self.lifecycle_manager:
            await self.lifecycle_manager.shutdown()
        
        logger.info("✓ Pipeline shutdown complete")
    
    async def process_files(
        self,
        file_paths: List[Path],
        progress_callback: Optional[callable] = None
    ) -> PipelineResult:
        """
        Process batch of files through the pipeline.
        
        Args:
            file_paths: List of PDF file paths
            progress_callback: Optional callback for progress updates
            
        Returns:
            PipelineResult with statistics and details
        """
        start_time = datetime.now()
        self.progress_callback = progress_callback
        self.failed_files = []
        
        logger.info("\n" + "=" * 70)
        logger.info(f"Starting pipeline processing for {len(file_paths)} files")
        logger.info("=" * 70)
        
        try:
            # Stage 1: PDF Processing (Parallel)
            logger.info("\n[Stage 1/4] PDF Processing (Parallel)")
            pdf_results = await self.pdf_stage.process_batch(
                file_paths,
                progress_callback=self._create_stage_callback("pdf", progress_callback)
            )
            
            successful_pdfs = [r for r in pdf_results if r.success]
            failed_pdfs = [r for r in pdf_results if not r.success]
            skipped_pdfs = [r for r in pdf_results if r.skipped]
            
            logger.info(f"✓ PDF Stage: {len(successful_pdfs)}/{len(pdf_results)} successful, {len(skipped_pdfs)} skipped (duplicates)")
            
            # Track failed PDFs
            for failed in failed_pdfs:
                self.failed_files.append({
                    "file_path": str(failed.file_path),
                    "stage": "pdf_processing",
                    "error": failed.error
                })
            
            # Filter out skipped files - don't process them further!
            files_to_process = [r for r in successful_pdfs if not r.skipped]
            
            if not files_to_process:
                logger.warning("No new files to process (all duplicates or failed)")
                return self._create_result(start_time, pdf_results, [], [], skipped_count=len(skipped_pdfs))
            
            # Stage 2 & 3: Extraction + Embedding (either via Haystack wrapper or internal stages)
            # Stage 2 & 3: Always run via Haystack wrapper (Extraction + Embedding)
            logger.info(f"\n[Stage 2/3] Haystack Wrapper (Extraction + Embedding)")
            documents = [r.document for r in files_to_process]
            # The wrapper returns paired tuples (extraction_result, embedding_result)
            paired_results = await self.haystack_wrapper.process_batch(
                documents,
                progress_callback=self._create_stage_callback("haystack_wrapper", progress_callback)
            )

            # Unpack into separate lists and handle failures
            extraction_results = [p[0] for p in paired_results]
            embedding_results = [p[1] for p in paired_results]

            successful_extractions = [r for r in extraction_results if r.success]
            failed_extractions = [r for r in extraction_results if not r.success]

            successful_embeddings = [r for r in embedding_results if r.success]
            failed_embeddings = [r for r in embedding_results if not r.success]

            # Track failed extractions and embeddings
            for failed in failed_extractions:
                self.failed_files.append({
                    "file_id": failed.file_id,
                    "original_filename": failed.original_filename,
                    "stage": "extraction",
                    "error": failed.error
                })

            for failed in failed_embeddings:
                self.failed_files.append({
                    "file_id": failed.file_id,
                    "original_filename": failed.original_filename,
                    "stage": "embedding",
                    "error": failed.error
                })

            if not successful_extractions or not successful_embeddings:
                logger.warning("No extractions/embeddings successful via Haystack wrapper")
                return self._create_result(start_time, pdf_results, extraction_results, embedding_results, skipped_count=len(skipped_pdfs))
            
            # Stage 4: Ingestion (Batched Weaviate writes)
            logger.info(f"\n[Stage 4/4] Weaviate Ingestion (Batched: {self.config.batch_size_weaviate})")
            
            # Pair extraction and embedding results
            results_pairs = list(zip(successful_extractions, successful_embeddings))
            
            ingestion_results = await self.ingestion_stage.process_batch(
                results_pairs,
                progress_callback=self._create_stage_callback("ingestion", progress_callback)
            )
            
            successful_ingestions = [r for r in ingestion_results if r.success and not r.skipped]
            skipped_ingestions = [r for r in ingestion_results if r.skipped]
            failed_ingestions = [r for r in ingestion_results if not r.success]
            
            logger.info(f"✓ Ingestion Stage: {len(successful_ingestions)} success, {len(skipped_ingestions)} skipped, {len(failed_ingestions)} failed")
            
            # Track failed ingestions
            for failed in failed_ingestions:
                self.failed_files.append({
                    "file_id": failed.file_id,
                    "original_filename": failed.original_filename,
                    "stage": "ingestion",
                    "error": failed.error
                })
            
            # Create final result
            return self._create_result(
                start_time,
                pdf_results,
                extraction_results,
                embedding_results,
                ingestion_results,
                skipped_count=len(skipped_pdfs)
            )
            
        except Exception as e:
            logger.error(f"Pipeline processing failed: {e}", exc_info=True)
            duration = (datetime.now() - start_time).total_seconds()
            
            return PipelineResult(
                total_files=len(file_paths),
                successful=0,
                failed=len(file_paths),
                skipped=0,
                duration_seconds=duration,
                results=[],
                failed_files=self.failed_files
            )
    
    async def process_with_retry(
        self,
        file_paths: List[Path],
        progress_callback: Optional[callable] = None
    ) -> PipelineResult:
        """
        Process files with automatic retry for failures.
        
        Args:
            file_paths: List of PDF file paths
            progress_callback: Optional callback for progress updates
            
        Returns:
            PipelineResult with statistics
        """
        # First attempt
        logger.info("=" * 70)
        logger.info("FIRST ATTEMPT")
        logger.info("=" * 70)
        
        result = await self.process_files(file_paths, progress_callback)
        
        # Retry failed files if auto-retry enabled
        if self.config.auto_retry_failed and result.failed_files:
            logger.info("\n" + "=" * 70)
            logger.info(f"RETRY ATTEMPT ({len(result.failed_files)} failed files)")
            logger.info("=" * 70)
            
            # Get file paths for failed files from first stage
            retry_paths = []
            for failed in result.failed_files:
                if failed["stage"] == "pdf_processing":
                    retry_paths.append(Path(failed["file_path"]))
            
            if retry_paths:
                logger.info(f"Retrying {len(retry_paths)} files...")
                
                retry_result = await self.process_files(retry_paths, progress_callback)
                
                # Merge results
                result.successful += retry_result.successful
                result.failed = len(retry_result.failed_files)
                result.results.extend(retry_result.results)
                result.failed_files = retry_result.failed_files
                
                logger.info(f"✓ Retry complete: {retry_result.successful} recovered")
        
        # Save failed files if configured
        if self.config.save_failed_files and result.failed_files:
            self._save_failed_files(result.failed_files)
        
        return result
    
    def _create_stage_callback(self, stage_name: str, user_callback: Optional[callable]):
        """Create callback wrapper for stage progress."""
        async def callback(*args, **kwargs):
            if user_callback:
                await user_callback(stage_name, *args, **kwargs)
        
        return callback if user_callback else None
    
    def _create_result(
        self,
        start_time: datetime,
        pdf_results: List = None,
        extraction_results: List = None,
        embedding_results: List = None,
        ingestion_results: List = None,
        skipped_count: int = 0
    ) -> PipelineResult:
        """Create final pipeline result."""
        duration = (datetime.now() - start_time).total_seconds()
        
        # Count final successes from ingestion stage
        successful = 0
        skipped = skipped_count  # Duplicates detected early in PDF stage
        
        if ingestion_results:
            successful = sum(1 for r in ingestion_results if r.success)
        
        total_files = len(pdf_results) if pdf_results else 0
        failed = len(self.failed_files)
        
        # Compile results
        results = []
        if ingestion_results:
            for r in ingestion_results:
                results.append({
                    "file_id": r.file_id,
                    "original_filename": r.original_filename,
                    "status": "skipped" if r.skipped else ("success" if r.success else "error"),
                    "sections_count": r.sections_count,
                    "chunks_count": r.chunks_count,
                    "error": r.error
                })
        
        return PipelineResult(
            total_files=total_files,
            successful=successful,
            failed=failed,
            skipped=skipped,
            duration_seconds=duration,
            results=results,
            failed_files=self.failed_files
        )
    
    def _save_failed_files(self, failed_files: List[Dict]) -> None:
        """Save failed files to JSON."""
        output_path = Path("logs/failed_files.json")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w') as f:
            json.dump({
                "timestamp": datetime.now().isoformat(),
                "total_failures": len(failed_files),
                "failures": failed_files
            }, f, indent=2)
        
        logger.info(f"✓ Failed files saved to {output_path}")
    
    def get_status(self) -> Dict[str, Any]:
        """Get pipeline status."""
        status = {
            "initialized": self.lifecycle_manager is not None,
            "stages": {
                "pdf": self.pdf_stage is not None,
                "extraction": self.extraction_stage is not None,
                "embedding": self.embedding_stage is not None,
                "ingestion": self.ingestion_stage is not None
            }
        }
        
        if self.lifecycle_manager:
            status["lifecycle"] = self.lifecycle_manager.get_status()
        
        return status


async def create_and_run_pipeline(
    file_paths: List[Path],
    config: Optional[Config] = None,
    skip_existing: bool = True,
    progress_callback: Optional[callable] = None
) -> PipelineResult:
    """
    Convenience function to create, run, and cleanup pipeline.
    
    Args:
        file_paths: List of PDF files to process
        config: Configuration instance
        skip_existing: Skip already ingested files
        progress_callback: Progress callback function
        
    Returns:
        PipelineResult
    """
    pipeline = OptimizedPipeline(config=config, skip_existing=skip_existing)
    
    try:
        # Initialize
        success = await pipeline.initialize()
        if not success:
            raise RuntimeError("Pipeline initialization failed")
        
        # Process files with retry
        result = await pipeline.process_with_retry(file_paths, progress_callback)
        
        return result
        
    finally:
        # Always cleanup
        await pipeline.shutdown()
