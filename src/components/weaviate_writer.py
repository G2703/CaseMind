"""
Stage 6: Weaviate Writer
Haystack component for batch upserting to Weaviate (4 collections).
"""

from typing import List, Dict, Any
import logging
import uuid
from datetime import datetime, timezone

from haystack import component, Document

from src.infrastructure.weaviate_client import WeaviateClient
from weaviate.classes.query import Filter

logger = logging.getLogger(__name__)


@component
class WeaviateWriter:
    """
    Haystack component for writing to Weaviate collections.
    Writes to 4 collections: CaseDocuments, CaseMetadata, CaseSections, CaseChunks.
    
    Inputs:
        - documents (List[Document]): Documents with metadata
        - chunks (List[Dict]): Chunks with embeddings
        - extractions (List[Dict]): Comprehensive extractions
        - sections (List[Dict]): Sections with embeddings
    
    Outputs:
        - results (List[Dict]): Ingestion results per document
    """
    
    # Namespace for deterministic UUID generation
    NAMESPACE = uuid.UUID('6ba7b810-9dad-11d1-80b4-00c04fd430c8')
    
    def __init__(self, skip_existing: bool = True):
        """
        Initialize Weaviate writer.
        
        Args:
            skip_existing: Skip documents that already exist in Weaviate
        """
        self.weaviate_client = WeaviateClient()
        self.skip_existing = skip_existing
        logger.info("WeaviateWriter initialized")
    
    @component.output_types(results=List[Dict[str, Any]])
    def run(
        self,
        documents: List[Document],
        chunks: List[Dict[str, Any]],
        extractions: List[Dict[str, Any]],
        sections: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Write documents, metadata, sections, and chunks to Weaviate.
        
        Args:
            documents: Haystack documents with metadata
            chunks: Text chunks with embeddings
            extractions: Comprehensive extractions
            sections: Case sections with embeddings
            
        Returns:
            Dictionary with 'results' key containing ingestion results
        """
        results = []
        client = self.weaviate_client.client
        
        for doc in documents:
            # Skip error documents
            if "error" in doc.meta:
                results.append({
                    "file_id": "",
                    "status": "error",
                    "message": doc.meta["error"],
                    "original_filename": doc.meta.get("original_filename", "unknown"),
                    "error_details": {
                        "stage": doc.meta.get("error_stage", "unknown"),
                        "error_type": "PipelineError",
                        "error_message": doc.meta["error"]
                    }
                })
                continue
            
            file_id = doc.meta.get("file_id", "")
            md_hash = doc.meta.get("md_hash", "")
            original_filename = doc.meta.get("original_filename", "unknown")
            
            # Check if already ingested
            if self.skip_existing:
                doc_collection = client.collections.get("CaseDocuments")
                existing = doc_collection.query.fetch_objects(
                    filters=Filter.by_property("file_id").equal(file_id),
                    limit=1
                )
                
                if existing.objects:
                    logger.warning(f"Document already ingested: {file_id}")
                    results.append({
                        "file_id": file_id,
                        "status": "skipped",
                        "message": "Document already exists",
                        "original_filename": original_filename
                    })
                    continue
            
            try:
                # Write to all 4 collections (transactional-style)
                self._write_document(client, doc, file_id, md_hash)
                self._write_metadata(client, doc, file_id)
                self._write_sections(client, sections, file_id)
                self._write_chunks(client, chunks, file_id)
                
                # Count what was written
                doc_sections = [s for s in sections if s["file_id"] == file_id]
                doc_chunks = [c for c in chunks if c["file_id"] == file_id]
                
                results.append({
                    "file_id": file_id,
                    "md_hash": md_hash,
                    "status": "success",
                    "message": f"Ingested: {len(doc_sections)} sections, {len(doc_chunks)} chunks",
                    "original_filename": original_filename,
                    "sections_count": len(doc_sections),
                    "chunks_count": len(doc_chunks)
                })
                
                logger.info(f"✓ Ingested {original_filename}: {len(doc_sections)} sections, {len(doc_chunks)} chunks")
                
            except Exception as e:
                # Rollback: cleanup any partial writes
                logger.error(f"Failed to ingest {original_filename}: {e}")
                logger.info(f"Rolling back partial writes for {file_id}...")
                
                try:
                    self._cleanup_partial_ingestion(client, file_id)
                    logger.info(f"✓ Rollback successful for {file_id}")
                except Exception as cleanup_error:
                    logger.error(f"Rollback failed for {file_id}: {cleanup_error}")
                
                results.append({
                    "file_id": file_id,
                    "status": "error",
                    "message": str(e),
                    "original_filename": original_filename,
                    "error_details": {
                        "stage": "weaviate_writer",
                        "error_type": type(e).__name__,
                        "error_message": str(e)
                    }
                })
        
        # Summary statistics
        success_count = sum(1 for r in results if r["status"] == "success")
        skipped_count = sum(1 for r in results if r["status"] == "skipped")
        error_count = sum(1 for r in results if r["status"] == "error")
        
        logger.info(f"Batch write complete: {success_count} success, {skipped_count} skipped, {error_count} errors")
        
        return {"results": results}
    
    def _write_document(self, client, doc: Document, file_id: str, md_hash: str):
        """Write to CaseDocuments collection."""
        timestamp = datetime.now(timezone.utc).isoformat()
        
        doc_data = {
            "file_id": file_id,
            "md_hash": md_hash,
            "original_filename": doc.meta["original_filename"],
            "md_gcs_uri": doc.meta.get("md_uri", ""),
            "created_at": timestamp,
            "page_count": 0
        }
        
        doc_collection = client.collections.get("CaseDocuments")
        with doc_collection.batch.dynamic() as batch:
            batch.add_object(properties=doc_data, uuid=file_id)
        
        logger.debug(f"Wrote to CaseDocuments: {file_id}")
    
    def _write_metadata(self, client, doc: Document, file_id: str):
        """Write to CaseMetadata collection."""
        extraction = doc.meta.get("extraction")
        if not extraction:
            logger.warning(f"No extraction found for {file_id}, skipping metadata write")
            return
        
        metadata = extraction.metadata
        metadata_id = self._generate_metadata_id(file_id)
        
        metadata_data = {
            "metadata_id": metadata_id,
            "file_id": file_id,
            "case_number": metadata.case_number,
            "case_title": metadata.case_title,
            "court_name": metadata.court_name,
            "judgment_date": self._convert_to_rfc3339(metadata.judgment_date) if metadata.judgment_date else None,
            "sections_invoked": metadata.sections_invoked,
            "judges_coram": metadata.judges_coram,
            "petitioner": metadata.appellant_or_petitioner,
            "respondent": metadata.respondent,
            "case_type": metadata.case_type,
            "bench_strength": len(metadata.judges_coram) if metadata.judges_coram else 0,
            "citation": metadata.citation,
            "counsel_petitioner": metadata.counsel_for_appellant,
            "counsel_respondent": metadata.counsel_for_respondent,
            "most_appropriate_section": metadata.most_appropriate_section
        }
        
        metadata_collection = client.collections.get("CaseMetadata")
        with metadata_collection.batch.dynamic() as batch:
            batch.add_object(properties=metadata_data, uuid=metadata_id)
        
        logger.debug(f"Wrote to CaseMetadata: {metadata_id}")
    
    def _write_sections(self, client, sections: List[Dict], file_id: str):
        """Write to CaseSections collection."""
        doc_sections = [s for s in sections if s["file_id"] == file_id]
        
        if not doc_sections:
            return
        
        sections_collection = client.collections.get("CaseSections")
        
        with sections_collection.batch.dynamic() as batch:
            for section in doc_sections:
                section_id = self._generate_section_id(file_id, section["section_name"])
                section_data = {
                    "section_id": section_id,
                    "file_id": file_id,
                    "section_name": section["section_name"],
                    "sequence_number": section["sequence_number"],
                    "text": section["text"]
                }
                batch.add_object(
                    properties=section_data,
                    uuid=section_id,
                    vector=section.get("vector")
                )
        
        logger.debug(f"Wrote {len(doc_sections)} sections to CaseSections")
    
    def _write_chunks(self, client, chunks: List[Dict], file_id: str):
        """Write to CaseChunks collection."""
        doc_chunks = [c for c in chunks if c["file_id"] == file_id]
        
        if not doc_chunks:
            return
        
        chunks_collection = client.collections.get("CaseChunks")
        
        with chunks_collection.batch.dynamic() as batch:
            for chunk in doc_chunks:
                chunk_id = self._generate_chunk_id(file_id, chunk["chunk_index"])
                chunk_data = {
                    "chunk_id": chunk_id,
                    "file_id": file_id,
                    "chunk_index": chunk["chunk_index"],
                    "text": chunk["text"],
                    "token_count": chunk["token_count"]
                }
                batch.add_object(
                    properties=chunk_data,
                    uuid=chunk_id,
                    vector=chunk.get("vector")
                )
        
        logger.debug(f"Wrote {len(doc_chunks)} chunks to CaseChunks")
    
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
        """Convert various date formats to RFC3339 format for Weaviate."""
        from dateutil import parser
        try:
            dt = parser.parse(date_str)
            # Ensure timezone awareness
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.isoformat()
        except Exception as e:
            logger.warning(f"Failed to parse date '{date_str}': {e}. Using current date.")
            return datetime.now(timezone.utc).isoformat()
    
    def _cleanup_partial_ingestion(self, client, file_id: str):
        """
        Remove all records for a file_id from all 4 collections.
        Used for rollback when ingestion fails partway through.
        
        Args:
            client: Weaviate client
            file_id: File ID to clean up
        """
        collections_to_clean = [
            "CaseDocuments",
            "CaseMetadata",
            "CaseSections",
            "CaseChunks"
        ]
        
        for collection_name in collections_to_clean:
            try:
                collection = client.collections.get(collection_name)
                
                # Delete all objects with this file_id
                collection.data.delete_many(
                    where=Filter.by_property("file_id").equal(file_id)
                )
                
                logger.debug(f"Cleaned {collection_name} for file_id: {file_id}")
            
            except Exception as e:
                logger.warning(f"Failed to clean {collection_name} for {file_id}: {e}")
