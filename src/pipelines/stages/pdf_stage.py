"""
PDF Stage - Parallel PDF to Markdown conversion.
Uses multiple workers to process PDFs concurrently.
"""

import asyncio
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import hashlib

from src.components.pdf_to_markdown import PDFToMarkdownConverter
from src.components.markdown_normalizer import MarkdownNormalizer
from haystack import Document

logger = logging.getLogger(__name__)


@dataclass
class PDFResult:
    """Result from PDF processing."""
    file_path: Path
    document: Optional[Document] = None
    error: Optional[str] = None
    success: bool = False
    skipped: bool = False  # True if duplicate detected


class PDFStage:
    """
    Stage 1: Parallel PDF to Markdown conversion.
    Processes multiple PDFs concurrently using worker pool.
    Includes early duplicate detection to avoid unnecessary processing.
    """
    
    def __init__(self, num_workers: int = 3, weaviate_pool=None, skip_existing: bool = True):
        """
        Initialize PDF stage.
        
        Args:
            num_workers: Number of parallel workers
            weaviate_pool: Optional Weaviate connection pool for duplicate checking
            skip_existing: Skip files that already exist in Weaviate
        """
        self.num_workers = num_workers
        self.weaviate_pool = weaviate_pool
        self.skip_existing = skip_existing
        self.pdf_converter = PDFToMarkdownConverter()
        self.markdown_normalizer = MarkdownNormalizer()
        
        logger.info(f"PDFStage initialized with {num_workers} workers (skip_existing={skip_existing})")
    
    async def process_file(self, file_path: Path) -> PDFResult:
        """
        Process single PDF file.
        
        Args:
            file_path: Path to PDF file
            
        Returns:
            PDFResult with document or error
        """
        try:
            logger.debug(f"Processing PDF: {file_path.name}")
            
            # Run PDF conversion in executor (blocking operation)
            loop = asyncio.get_event_loop()
            pdf_result = await loop.run_in_executor(
                None,
                self._convert_pdf_sync,
                file_path
            )
            
            if not pdf_result or "error" in pdf_result:
                error_msg = pdf_result.get("error", "Unknown PDF conversion error") if pdf_result else "PDF conversion failed"
                logger.error(f"Failed to convert {file_path.name}: {error_msg}")
                return PDFResult(
                    file_path=file_path,
                    error=error_msg,
                    success=False
                )
            
            # Extract document from result
            documents = pdf_result.get("documents", [])
            if not documents:
                logger.error(f"No documents returned for {file_path.name}")
                return PDFResult(
                    file_path=file_path,
                    error="No documents generated",
                    success=False
                )
            
            doc = documents[0]
            
            # Run markdown normalization
            norm_result = await loop.run_in_executor(
                None,
                self._normalize_markdown_sync,
                doc
            )
            
            if not norm_result or "error" in norm_result:
                error_msg = norm_result.get("error", "Unknown normalization error") if norm_result else "Normalization failed"
                logger.error(f"Failed to normalize {file_path.name}: {error_msg}")
                return PDFResult(
                    file_path=file_path,
                    error=error_msg,
                    success=False
                )
            
            normalized_docs = norm_result.get("documents", [])
            if not normalized_docs:
                logger.error(f"No normalized documents for {file_path.name}")
                return PDFResult(
                    file_path=file_path,
                    error="Normalization produced no documents",
                    success=False
                )
            
            normalized_doc = normalized_docs[0]
            
            file_id = normalized_doc.meta.get('file_id', 'unknown')
            logger.info(f"✓ Converted PDF: {file_path.name} → {file_id}")
            
            # Early duplicate detection (skip expensive LLM calls)
            if self.skip_existing and self.weaviate_pool:
                is_duplicate = await self._check_duplicate(file_id, file_path.name)
                if is_duplicate:
                    logger.warning(f"⊘ Duplicate detected: {file_path.name} (file_id: {file_id}) - skipping further processing")
                    return PDFResult(
                        file_path=file_path,
                        document=normalized_doc,
                        success=True,
                        skipped=True  # Mark as skipped
                    )
            
            return PDFResult(
                file_path=file_path,
                document=normalized_doc,
                success=True,
                skipped=False
            )
            
        except Exception as e:
            logger.error(f"Error processing {file_path.name}: {e}", exc_info=True)
            return PDFResult(
                file_path=file_path,
                error=str(e),
                success=False
            )
    
    def _convert_pdf_sync(self, file_path: Path) -> Dict[str, Any]:
        """Synchronous PDF conversion (runs in executor)."""
        try:
            result = self.pdf_converter.run(file_paths=[file_path])
            return result
        except Exception as e:
            return {"error": str(e)}
    
    def _normalize_markdown_sync(self, document: Document) -> Dict[str, Any]:
        """Synchronous markdown normalization (runs in executor)."""
        try:
            result = self.markdown_normalizer.run(documents=[document])
            return result
        except Exception as e:
            return {"error": str(e)}
    
    async def _check_duplicate(self, file_id: str, filename: str) -> bool:
        """
        Check if document already exists in Weaviate.
        
        Args:
            file_id: File ID to check
            filename: Original filename (for logging)
            
        Returns:
            True if duplicate exists, False otherwise
        """
        try:
            async with self.weaviate_pool.acquire() as client:
                loop = asyncio.get_event_loop()
                exists = await loop.run_in_executor(
                    None,
                    self._check_duplicate_sync,
                    client,
                    file_id
                )
                return exists
        except Exception as e:
            logger.error(f"Duplicate check failed for {filename}: {e}")
            return False  # Continue processing on error
    
    def _check_duplicate_sync(self, client, file_id: str) -> bool:
        """Synchronous duplicate check."""
        from weaviate.classes.query import Filter
        
        doc_collection = client.client.collections.get("CaseDocuments")
        existing = doc_collection.query.fetch_objects(
            filters=Filter.by_property("file_id").equal(file_id),
            limit=1
        )
        
        return len(existing.objects) > 0
    
    async def process_batch(
        self,
        file_paths: List[Path],
        progress_callback: Optional[callable] = None
    ) -> List[PDFResult]:
        """
        Process batch of PDFs in parallel.
        
        Args:
            file_paths: List of PDF file paths
            progress_callback: Optional callback for progress updates
            
        Returns:
            List of PDFResults
        """
        logger.info(f"Processing {len(file_paths)} PDFs with {self.num_workers} workers...")
        
        # Create semaphore to limit concurrent workers
        semaphore = asyncio.Semaphore(self.num_workers)
        
        async def process_with_semaphore(file_path: Path) -> PDFResult:
            """Process file with semaphore to limit concurrency."""
            async with semaphore:
                result = await self.process_file(file_path)
                
                # Call progress callback if provided
                if progress_callback:
                    await progress_callback(result)
                
                return result
        
        # Process all files concurrently (limited by semaphore)
        tasks = [process_with_semaphore(fp) for fp in file_paths]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Handle any exceptions from gather
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Task exception for {file_paths[i].name}: {result}")
                processed_results.append(PDFResult(
                    file_path=file_paths[i],
                    error=str(result),
                    success=False
                ))
            else:
                processed_results.append(result)
        
        # Count successes and failures
        success_count = sum(1 for r in processed_results if r.success and not r.skipped)
        skipped_count = sum(1 for r in processed_results if r.skipped)
        failure_count = len(processed_results) - success_count - skipped_count
        
        logger.info(f"PDF processing complete: {success_count} success, {skipped_count} skipped (duplicates), {failure_count} failed")
        
        return processed_results
