"""
Haystack Wrapper Stage

This stage provides a low-risk adapter that runs the existing extraction
and embedding stages as a single, toggleable unit. It is intentionally a
lightweight adaptor so the optimized orchestrator keeps control over
pooling, rate-limiting, batching and single-writer semantics.

Usage:
  - Initialize with OpenAI and Embedding pools (same as existing stages).
  - Call `process_batch(documents)` to receive pairs of (ExtractionResult, EmbeddingResult).

This is a pragmatic wrapper implementation (recommended first step).
"""

import asyncio
import logging
from typing import List, Optional, Tuple

from haystack import Document

from src.core.config import Config
from src.core.pools import OpenAIClientPool, EmbeddingClientPool
from src.pipelines.stages.extraction_stage import ExtractionStage, ExtractionResult
from src.pipelines.stages.embedding_stage import EmbeddingStage, EmbeddingResult

logger = logging.getLogger(__name__)


class HaystackWrapperStage:
    """Adapter that runs extraction + embedding as a single stage.

    Internally reuses the existing `ExtractionStage` and `EmbeddingStage` but
    exposes a single `process_batch` method that returns paired results which
    the orchestrator can forward to ingestion directly.
    """

    def __init__(self, config: Optional[Config] = None):
        self.config = config or Config()
        self.extraction_stage: Optional[ExtractionStage] = None
        self.embedding_stage: Optional[EmbeddingStage] = None
        self.openai_pool: Optional[OpenAIClientPool] = None
        self.embedding_pool: Optional[EmbeddingClientPool] = None

        logger.info("HaystackWrapperStage initialized")

    async def initialize(self, openai_pool: OpenAIClientPool, embedding_pool: EmbeddingClientPool) -> None:
        """Initialize underlying stages with shared pools."""
        self.openai_pool = openai_pool
        self.embedding_pool = embedding_pool

        # Create underlying stages and initialize with pools
        self.extraction_stage = ExtractionStage(config=self.config)
        await self.extraction_stage.initialize(openai_pool)

        self.embedding_stage = EmbeddingStage(config=self.config)
        await self.embedding_stage.initialize(embedding_pool)

        logger.info("HaystackWrapperStage connected to OpenAI and Embedding pools")

    async def process_batch(self, documents: List[Document], progress_callback: Optional[callable] = None) -> List[Tuple[ExtractionResult, EmbeddingResult]]:
        """Process documents: extract then embed and return paired results.

        Returns a list of tuples: (ExtractionResult, EmbeddingResult).
        """
        if not self.extraction_stage or not self.embedding_stage:
            raise RuntimeError("HaystackWrapperStage not initialized")

        logger.info(f"HaystackWrapperStage: processing {len(documents)} documents")

        # Extraction (rate-limited, sequential)
        extraction_results = await self.extraction_stage.process_batch(documents, progress_callback=progress_callback)

        # Keep only successful extractions for embedding
        successful_extractions = [r for r in extraction_results if r.success]

        if not successful_extractions:
            logger.warning("HaystackWrapperStage: no successful extractions to embed")
            return []

        # Embedding (batched/optimized)
        embedding_results = await self.embedding_stage.process_batch_optimized(successful_extractions, progress_callback=progress_callback)

        # Pair extraction and embedding results by file_id
        embedding_by_file = {e.file_id: e for e in embedding_results}

        paired = []
        for ex in successful_extractions:
            emb = embedding_by_file.get(ex.file_id)
            if emb:
                paired.append((ex, emb))
            else:
                # Create a failed embedding placeholder
                failed_emb = EmbeddingResult(
                    file_id=ex.file_id,
                    original_filename=ex.original_filename,
                    error="embedding_missing",
                    success=False
                )
                paired.append((ex, failed_emb))

        logger.info(f"HaystackWrapperStage: paired {len(paired)} extraction+embedding results")
        return paired
