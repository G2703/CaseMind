"""
Ingestion Stage - Batched Weaviate writes.
Buffers objects and writes in large batches for efficiency.
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime, timezone
import uuid

from src.core.pools import WeaviateConnectionPool
from src.core.config import Config
from weaviate.classes.query import Filter

logger = logging.getLogger(__name__)


@dataclass
class IngestionResult:
    """Result from ingestion processing."""
    file_id: str
    original_filename: str
    sections_count: int = 0
    chunks_count: int = 0
    error: Optional[str] = None
    success: bool = False
    skipped: bool = False


class IngestionStage:
    """
    Stage 4: Batched Weaviate ingestion.
    Writes documents, metadata, sections, and chunks to Weaviate.
    """
    
    # Namespace for deterministic UUID generation
    NAMESPACE = uuid.UUID('6ba7b810-9dad-11d1-80b4-00c04fd430c8')
    
    def __init__(self, skip_existing: bool = True, config: Optional[Config] = None):
        """
        Initialize ingestion stage.
        
        Args:
            skip_existing: Skip documents that already exist
            config: Configuration instance
        """
        self.skip_existing = skip_existing
        self.config = config or Config()
        self.weaviate_pool: Optional[WeaviateConnectionPool] = None
        self.batch_size = self.config.batch_size_weaviate
        
        logger.info(f"IngestionStage initialized (batch_size: {self.batch_size})")
    
    async def initialize(self, weaviate_pool: WeaviateConnectionPool) -> None:
        """
        Initialize with Weaviate pool.
        
        Args:
            weaviate_pool: Initialized Weaviate connection pool
        """
        self.weaviate_pool = weaviate_pool
        logger.info("IngestionStage connected to Weaviate pool")
    
    async def process_result(
        self,
        extraction_result,
        embedding_result,
        progress_callback: Optional[callable] = None
    ) -> IngestionResult:
        """
        Ingest a single document to Weaviate.
        
        Args:
            extraction_result: Result from extraction stage
            embedding_result: Result from embedding stage
            progress_callback: Optional callback for progress updates
            
        Returns:
            IngestionResult
        """
        file_id = extraction_result.file_id
        filename = extraction_result.original_filename
        
        try:
            if not extraction_result.success or not embedding_result.success:
                logger.warning(f"Skipping ingestion for failed document: {filename}")
                return IngestionResult(
                    file_id=file_id,
                    original_filename=filename,
                    error="Extraction or embedding failed",
                    success=False
                )
            
            if progress_callback:
                await progress_callback("ingestion", filename)
            
            # Check if already exists
            if self.skip_existing:
                # Also update and consult in-memory md_hash cache if available
                existing_set = getattr(self.weaviate_pool, 'existing_md_hashes', None)
                md_hash = extraction_result.document.meta.get('md_hash', '')
                if existing_set is not None:
                    if md_hash in existing_set:
                        logger.info(f"Skipping existing document (in-memory): {filename}")
                        return IngestionResult(
                            file_id=file_id,
                            original_filename=filename,
                            skipped=True,
                            success=True
                        )
                else:
                    exists = await self._check_exists(file_id)
                    if exists:
                        logger.info(f"Skipping existing document: {filename}")
                        return IngestionResult(
                            file_id=file_id,
                            original_filename=filename,
                            skipped=True,
                            success=True
                        )
            
            # Write to Weaviate
            # Acquire single-writer lock if available to avoid races
            write_lock = getattr(self.weaviate_pool, 'write_lock', None)
            if write_lock:
                async with write_lock:
                    async with self.weaviate_pool.acquire() as client:
                        await self._write_document(client, extraction_result)
                        await self._write_metadata(client, extraction_result)
                        await self._write_sections(client, embedding_result)
                        await self._write_chunks(client, embedding_result)
            else:
                async with self.weaviate_pool.acquire() as client:
                    await self._write_document(client, extraction_result)
                    await self._write_metadata(client, extraction_result)
                    await self._write_sections(client, embedding_result)
                    await self._write_chunks(client, embedding_result)
            
            sections_count = len(embedding_result.sections_with_embeddings or [])
            chunks_count = len(embedding_result.chunks_with_embeddings or [])
            
            logger.info(f"✓ Ingested {filename}: {sections_count} sections, {chunks_count} chunks")

            # Update in-memory md_hash set after successful ingestion
            try:
                existing_set = getattr(self.weaviate_pool, 'existing_md_hashes', None)
                md_hash = extraction_result.document.meta.get('md_hash', '')
                if existing_set is not None and md_hash:
                    existing_set.add(md_hash)
            except Exception:
                pass
            
            return IngestionResult(
                file_id=file_id,
                original_filename=filename,
                sections_count=sections_count,
                chunks_count=chunks_count,
                success=True
            )
            
        except Exception as e:
            logger.error(f"Ingestion failed for {filename}: {e}", exc_info=True)
            
            # Attempt rollback
            try:
                await self._cleanup_partial_ingestion(file_id)
            except Exception as cleanup_error:
                logger.error(f"Rollback failed for {file_id}: {cleanup_error}")
            
            return IngestionResult(
                file_id=file_id,
                original_filename=filename,
                error=str(e),
                success=False
            )
    
    async def _check_exists(self, file_id: str) -> bool:
        """Check if document already exists."""
        async with self.weaviate_pool.acquire() as client:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                self._check_exists_sync,
                client,
                file_id
            )
            return result
    
    def _check_exists_sync(self, client, file_id: str) -> bool:
        """Synchronous existence check."""
        doc_collection = client.client.collections.get("CaseDocuments")
        existing = doc_collection.query.fetch_objects(
            filters=Filter.by_property("file_id").equal(file_id),
            limit=1
        )
        return len(existing.objects) > 0
    
    async def _write_document(self, client, extraction_result) -> None:
        """Write to CaseDocuments collection."""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            self._write_document_sync,
            client,
            extraction_result
        )
    
    def _write_document_sync(self, client, extraction_result) -> None:
        """Synchronous document write."""
        timestamp = datetime.now(timezone.utc).isoformat()
        
        doc_data = {
            "file_id": extraction_result.file_id,
            "md_hash": extraction_result.document.meta.get("md_hash", ""),
            "original_filename": extraction_result.original_filename,
            "md_gcs_uri": extraction_result.document.meta.get("md_uri", ""),
            "created_at": timestamp,
            "page_count": 0
        }
        
        doc_collection = client.client.collections.get("CaseDocuments")
        with doc_collection.batch.dynamic() as batch:
            batch.add_object(properties=doc_data, uuid=extraction_result.file_id)
    
    async def _write_metadata(self, client, extraction_result) -> None:
        """Write to CaseMetadata collection."""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            self._write_metadata_sync,
            client,
            extraction_result
        )
    
    def _write_metadata_sync(self, client, extraction_result) -> None:
        """Synchronous metadata write."""
        extraction = extraction_result.extraction
        metadata = extraction.get("metadata", {})
        
        metadata_id = self._generate_metadata_id(extraction_result.file_id)
        
        # Ensure list fields are lists and string fields are strings
        sections_invoked = metadata.get("sections_invoked", [])
        if not isinstance(sections_invoked, list):
            sections_invoked = [sections_invoked] if sections_invoked else []
        
        judges_coram = metadata.get("judges_coram", [])
        if not isinstance(judges_coram, list):
            judges_coram = [judges_coram] if judges_coram else []
        
        # Ensure counsel fields are strings (not lists)
        counsel_for_appellant = metadata.get("counsel_for_appellant")
        if isinstance(counsel_for_appellant, list):
            counsel_for_appellant = ", ".join(counsel_for_appellant) if counsel_for_appellant else None
        
        counsel_for_respondent = metadata.get("counsel_for_respondent")
        if isinstance(counsel_for_respondent, list):
            counsel_for_respondent = ", ".join(counsel_for_respondent) if counsel_for_respondent else None
        
        metadata_data = {
            "metadata_id": metadata_id,
            "file_id": extraction_result.file_id,
            "case_number": metadata.get("case_number"),
            "case_title": metadata.get("case_title"),
            "court_name": metadata.get("court_name"),
            "judgment_date": self._convert_to_rfc3339(metadata.get("judgment_date")) if metadata.get("judgment_date") else None,
            "sections_invoked": sections_invoked,
            "judges_coram": judges_coram,
            "appellant_or_petitioner": metadata.get("appellant_or_petitioner"),
            "respondent": metadata.get("respondent"),
            "case_type": metadata.get("case_type"),
            "bench_strength": len(judges_coram),
            "citation": metadata.get("citation"),
            "counsel_for_appellant": counsel_for_appellant,
            "counsel_for_respondent": counsel_for_respondent,
            "most_appropriate_section": metadata.get("most_appropriate_section")
        }
        
        metadata_collection = client.client.collections.get("CaseMetadata")
        with metadata_collection.batch.dynamic() as batch:
            batch.add_object(properties=metadata_data, uuid=metadata_id)
    
    async def _write_sections(self, client, embedding_result) -> None:
        """Write to CaseSections collection."""
        if not embedding_result.sections_with_embeddings:
            return
        
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            self._write_sections_sync,
            client,
            embedding_result
        )
    
    def _write_sections_sync(self, client, embedding_result) -> None:
        """Synchronous sections write."""
        sections_collection = client.client.collections.get("CaseSections")
        
        with sections_collection.batch.dynamic() as batch:
            for section in embedding_result.sections_with_embeddings:
                section_id = self._generate_section_id(
                    embedding_result.file_id,
                    section["section_name"]
                )
                section_data = {
                    "section_id": section_id,
                    "file_id": embedding_result.file_id,
                    "section_name": section["section_name"],
                    "sequence_number": section["sequence_number"],
                    "text": section["text"]
                }
                batch.add_object(
                    properties=section_data,
                    uuid=section_id,
                    vector=section.get("vector")
                )
    
    async def _write_chunks(self, client, embedding_result) -> None:
        """Write to CaseChunks collection."""
        if not embedding_result.chunks_with_embeddings:
            return
        
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            self._write_chunks_sync,
            client,
            embedding_result
        )
    
    def _write_chunks_sync(self, client, embedding_result) -> None:
        """Synchronous chunks write."""
        chunks_collection = client.client.collections.get("CaseChunks")
        
        with chunks_collection.batch.dynamic() as batch:
            for chunk in embedding_result.chunks_with_embeddings:
                chunk_id = self._generate_chunk_id(
                    embedding_result.file_id,
                    chunk["chunk_index"]
                )
                chunk_data = {
                    "chunk_id": chunk_id,
                    "file_id": embedding_result.file_id,
                    "chunk_index": chunk["chunk_index"],
                    "text": chunk["text"],
                    "token_count": chunk["token_count"]
                }
                batch.add_object(
                    properties=chunk_data,
                    uuid=chunk_id,
                    vector=chunk.get("vector")
                )
    
    async def _cleanup_partial_ingestion(self, file_id: str) -> None:
        """Cleanup partial ingestion on error."""
        async with self.weaviate_pool.acquire() as client:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                self._cleanup_sync,
                client,
                file_id
            )
    
    def _cleanup_sync(self, client, file_id: str) -> None:
        """Synchronous cleanup."""
        collections = ["CaseDocuments", "CaseMetadata", "CaseSections", "CaseChunks"]
        
        for collection_name in collections:
            try:
                collection = client.client.collections.get(collection_name)
                collection.data.delete_many(
                    where=Filter.by_property("file_id").equal(file_id)
                )
            except Exception as e:
                logger.warning(f"Cleanup failed for {collection_name}: {e}")
    
    def _generate_metadata_id(self, file_id: str) -> str:
        """Generate deterministic metadata_id."""
        composite = f"{file_id}::metadata"
        return str(uuid.uuid5(self.NAMESPACE, composite))
    
    def _generate_section_id(self, file_id: str, section_name: str) -> str:
        """Generate deterministic section_id."""
        composite = f"{file_id}::{section_name}"
        return str(uuid.uuid5(self.NAMESPACE, composite))
    
    def _generate_chunk_id(self, file_id: str, chunk_index: int) -> str:
        """Generate deterministic chunk_id."""
        composite = f"{file_id}::chunk::{chunk_index}"
        return str(uuid.uuid5(self.NAMESPACE, composite))
    
    def _convert_to_rfc3339(self, date_str: str) -> str:
        """Convert date to RFC3339 format."""
        from dateutil import parser
        try:
            dt = parser.parse(date_str)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.isoformat()
        except Exception:
            return datetime.now(timezone.utc).isoformat()
    
    async def process_batch(
        self,
        results_pairs: List[tuple],
        progress_callback: Optional[callable] = None
    ) -> List[IngestionResult]:
        """
        Process batch of (extraction_result, embedding_result) pairs.
        
        Args:
            results_pairs: List of (extraction_result, embedding_result) tuples
            progress_callback: Optional callback for progress updates
            
        Returns:
            List of IngestionResults
        """
        logger.info(f"Ingesting {len(results_pairs)} documents to Weaviate...")
        
        results = []
        
        for extraction_result, embedding_result in results_pairs:
            result = await self.process_result(
                extraction_result,
                embedding_result,
                progress_callback
            )
            results.append(result)
        
        success_count = sum(1 for r in results if r.success and not r.skipped)
        skipped_count = sum(1 for r in results if r.skipped)
        failure_count = len(results) - success_count - skipped_count
        
        logger.info(f"Ingestion complete: {success_count} success, {skipped_count} skipped, {failure_count} failed")
        
        return results
