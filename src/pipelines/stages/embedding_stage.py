"""
Embedding Stage - Batched embedding generation.
Accumulates texts from multiple files and processes in large batches.
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from src.core.pools import EmbeddingModelPool
from src.core.queues import BatchAccumulator
from src.core.config import Config

logger = logging.getLogger(__name__)


@dataclass
class EmbeddingResult:
    """Result from embedding processing."""
    file_id: str
    original_filename: str
    sections_with_embeddings: Optional[List[Dict]] = None
    chunks_with_embeddings: Optional[List[Dict]] = None
    error: Optional[str] = None
    success: bool = False


class EmbeddingStage:
    """
    Stage 3: Batched embedding generation.
    Accumulates texts and processes in large batches for efficiency.
    """
    
    def __init__(self, config: Optional[Config] = None):
        """
        Initialize embedding stage.
        
        Args:
            config: Configuration instance
        """
        self.config = config or Config()
        self.embedding_pool: Optional[EmbeddingModelPool] = None
        self.batch_size = self.config.batch_size_embedding
        
        logger.info(f"EmbeddingStage initialized (batch_size: {self.batch_size})")
    
    async def initialize(self, embedding_pool: EmbeddingModelPool) -> None:
        """
        Initialize with embedding pool.
        
        Args:
            embedding_pool: Initialized embedding model pool
        """
        self.embedding_pool = embedding_pool
        logger.info("EmbeddingStage connected to embedding pool")
    
    async def process_result(
        self,
        extraction_result,
        progress_callback: Optional[callable] = None
    ) -> EmbeddingResult:
        """
        Process extraction result and generate embeddings.
        
        Args:
            extraction_result: Result from extraction stage
            progress_callback: Optional callback for progress updates
            
        Returns:
            EmbeddingResult with embeddings added
        """
        file_id = extraction_result.file_id
        filename = extraction_result.original_filename
        
        try:
            if not extraction_result.success:
                logger.warning(f"Skipping embedding for failed extraction: {filename}")
                return EmbeddingResult(
                    file_id=file_id,
                    original_filename=filename,
                    error="Extraction failed",
                    success=False
                )
            
            if progress_callback:
                await progress_callback("embedding", filename)
            
            # Generate embeddings for sections
            sections_with_embeddings = []
            if extraction_result.sections:
                section_texts = [s["text"] for s in extraction_result.sections]
                section_embeddings = await self.embedding_pool.encode_batch(
                    section_texts,
                    normalize=True,
                    batch_size=self.batch_size
                )
                
                for section, embedding in zip(extraction_result.sections, section_embeddings):
                    section_with_emb = section.copy()
                    section_with_emb["vector"] = embedding
                    sections_with_embeddings.append(section_with_emb)
                
                logger.debug(f"Generated embeddings for {len(sections_with_embeddings)} sections")
            
            # Generate embeddings for chunks
            chunks_with_embeddings = []
            if extraction_result.chunks:
                chunk_texts = [c["text"] for c in extraction_result.chunks]
                chunk_embeddings = await self.embedding_pool.encode_batch(
                    chunk_texts,
                    normalize=True,
                    batch_size=self.batch_size
                )
                
                for chunk, embedding in zip(extraction_result.chunks, chunk_embeddings):
                    chunk_with_emb = chunk.copy()
                    chunk_with_emb["vector"] = embedding
                    chunks_with_embeddings.append(chunk_with_emb)
                
                logger.debug(f"Generated embeddings for {len(chunks_with_embeddings)} chunks")
            
            logger.info(f"✓ Embeddings generated for {filename}")
            
            return EmbeddingResult(
                file_id=file_id,
                original_filename=filename,
                sections_with_embeddings=sections_with_embeddings,
                chunks_with_embeddings=chunks_with_embeddings,
                success=True
            )
            
        except Exception as e:
            logger.error(f"Embedding generation failed for {filename}: {e}", exc_info=True)
            return EmbeddingResult(
                file_id=file_id,
                original_filename=filename,
                error=str(e),
                success=False
            )
    
    async def process_batch_optimized(
        self,
        extraction_results: List,
        progress_callback: Optional[callable] = None
    ) -> List[EmbeddingResult]:
        """
        Process batch with optimized batching (accumulate all texts, embed once).
        
        Args:
            extraction_results: List of extraction results
            progress_callback: Optional callback for progress updates
            
        Returns:
            List of EmbeddingResults
        """
        logger.info(f"Processing embeddings for {len(extraction_results)} documents...")
        
        if not self.embedding_pool:
            raise RuntimeError("Embedding pool not initialized")
        
        # Accumulate all texts across all documents
        all_section_texts = []
        all_chunk_texts = []
        section_mapping = []  # (doc_idx, section_idx)
        chunk_mapping = []    # (doc_idx, chunk_idx)
        
        for doc_idx, result in enumerate(extraction_results):
            if not result.success:
                continue
            
            # Collect section texts
            if result.sections:
                for section_idx, section in enumerate(result.sections):
                    all_section_texts.append(section["text"])
                    section_mapping.append((doc_idx, section_idx))
            
            # Collect chunk texts
            if result.chunks:
                for chunk_idx, chunk in enumerate(result.chunks):
                    all_chunk_texts.append(chunk["text"])
                    chunk_mapping.append((doc_idx, chunk_idx))
        
        logger.info(f"Batching: {len(all_section_texts)} sections + {len(all_chunk_texts)} chunks")
        
        # Generate all embeddings in large batches
        section_embeddings = []
        chunk_embeddings = []
        
        if all_section_texts:
            if progress_callback:
                await progress_callback("embedding_sections", f"{len(all_section_texts)} sections")
            
            section_embeddings = await self.embedding_pool.encode_batch(
                all_section_texts,
                normalize=True,
                batch_size=self.batch_size
            )
            logger.info(f"✓ Generated {len(section_embeddings)} section embeddings")
        
        if all_chunk_texts:
            if progress_callback:
                await progress_callback("embedding_chunks", f"{len(all_chunk_texts)} chunks")
            
            chunk_embeddings = await self.embedding_pool.encode_batch(
                all_chunk_texts,
                normalize=True,
                batch_size=self.batch_size
            )
            logger.info(f"✓ Generated {len(chunk_embeddings)} chunk embeddings")
        
        # Distribute embeddings back to documents
        results = []
        
        for doc_idx, extraction_result in enumerate(extraction_results):
            if not extraction_result.success:
                results.append(EmbeddingResult(
                    file_id=extraction_result.file_id,
                    original_filename=extraction_result.original_filename,
                    error=extraction_result.error,
                    success=False
                ))
                continue
            
            # Get sections for this document
            sections_with_embeddings = []
            for emb_idx, (d_idx, s_idx) in enumerate(section_mapping):
                if d_idx == doc_idx:
                    section = extraction_result.sections[s_idx].copy()
                    section["vector"] = section_embeddings[emb_idx]
                    sections_with_embeddings.append(section)
            
            # Get chunks for this document
            chunks_with_embeddings = []
            for emb_idx, (d_idx, c_idx) in enumerate(chunk_mapping):
                if d_idx == doc_idx:
                    chunk = extraction_result.chunks[c_idx].copy()
                    chunk["vector"] = chunk_embeddings[emb_idx]
                    chunks_with_embeddings.append(chunk)
            
            results.append(EmbeddingResult(
                file_id=extraction_result.file_id,
                original_filename=extraction_result.original_filename,
                sections_with_embeddings=sections_with_embeddings,
                chunks_with_embeddings=chunks_with_embeddings,
                success=True
            ))
        
        success_count = sum(1 for r in results if r.success)
        logger.info(f"Embedding stage complete: {success_count}/{len(results)} success")
        
        return results
