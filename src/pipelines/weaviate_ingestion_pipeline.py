"""
Weaviate Ingestion Pipeline for CaseMind.
Orchestrates PDF → Markdown → Chunks/Sections → Embeddings → Weaviate flow.
"""

import sys
import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import asdict
import uuid
from datetime import datetime, timezone

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from src.core.config import Config
from src.core.models import (
    CaseSection,
    TextChunk,
    WeaviateMetadata,
    WeaviateIngestionResult
)
from src.infrastructure.weaviate_client import WeaviateClient
from src.infrastructure.storage_adapter import LocalStorageAdapter
from src.services.markdown_service import MarkdownService
from src.services.chunking_service import ChunkingService
from src.services.extraction_service import ExtractionService
from src.services.embedding_service import EmbeddingService
from src.services.pdf_extraction_service import PDFExtractionService
from src.utils.logger import get_logger

logger = get_logger(__name__)


class WeaviateIngestionPipeline:
    """
    Orchestrates the complete ingestion pipeline from PDF to Weaviate collections.
    
    Pipeline stages:
    1. PDF → Markdown extraction
    2. Markdown normalization & storage (content-addressed)
    3. Text chunking (512 tokens, 10% overlap)
    4a. summary_extraction: Extract comprehensive summary from markdown (main_template.json format)
        - Extracts: metadata, case_facts, evidence, arguments, reasoning, judgement
        - Identifies: most_appropriate_section
    4b. template_fact_extraction: Extract template-specific facts from summary (NOT markdown)
        - Uses: most_appropriate_section to load specific template
        - Inputs: template_schema, case_facts, evidence, arguments, reasoning, judgement (from summary)
        - Extracts: tier_1_determinative, tier_2_material, tier_3_contextual, residual_details
    5. Batch embedding generation (768-d vectors)
    6. Weaviate batch upsert (4 collections)
    7. Result verification
    """
    
    # Namespace for deterministic UUID generation
    NAMESPACE = uuid.UUID('6ba7b810-9dad-11d1-80b4-00c04fd430c8')  # UUID namespace for DNS
    
    def __init__(self, config: Optional[Config] = None):
        """Initialize pipeline with all required services."""
        self.config = config or Config()
        
        # Initialize services
        self.weaviate_client = WeaviateClient()
        self.storage_adapter = LocalStorageAdapter(self.config.local_storage_path)
        self.markdown_service = MarkdownService(self.storage_adapter)
        self.chunking_service = ChunkingService()
        self.extraction_service = ExtractionService(self.config)
        self.embedding_service = EmbeddingService()
        self.pdf_extraction_service = PDFExtractionService()
        
        logger.info("WeaviateIngestionPipeline initialized")
    
    def _generate_file_id(self, md_hash: str) -> str:
        """Generate deterministic file_id from md_hash using UUID5."""
        return str(uuid.uuid5(self.NAMESPACE, md_hash))
    
    def _generate_section_id(self, file_id: str, section_name: str) -> str:
        """Generate deterministic section_id."""
        composite = f"{file_id}::{section_name}"
        return str(uuid.uuid5(self.NAMESPACE, composite))
    
    def _generate_chunk_id(self, file_id: str, chunk_index: int) -> str:
        """Generate deterministic chunk_id."""
        composite = f"{file_id}::chunk::{chunk_index}"
        return str(uuid.uuid5(self.NAMESPACE, composite))
    
    def _generate_metadata_id(self, file_id: str) -> str:
        """Generate deterministic metadata_id."""
        composite = f"{file_id}::metadata"
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
    
    def _create_sections_from_extraction(self, extraction) -> List[CaseSection]:
        """Create CaseSection objects from ComprehensiveExtraction."""
        sections = []
        
        # Case Facts section
        if extraction.case_facts and extraction.case_facts.prosecution_version:
            sections.append(CaseSection(
                section_name="Case Facts",
                sequence_number=0,
                text=f"Prosecution: {extraction.case_facts.prosecution_version}\n\nDefence: {extraction.case_facts.defence_version}"
            ))
        
        # Evidence section
        if extraction.evidence:
            evidence_text = f"Medical Evidence: {extraction.evidence.medical_evidence}\n\n"
            evidence_text += f"Forensic Evidence: {extraction.evidence.forensic_evidence}\n\n"
            evidence_text += f"Investigation: {extraction.evidence.investigation_findings}"
            sections.append(CaseSection(
                section_name="Evidence",
                sequence_number=1,
                text=evidence_text
            ))
        
        # Arguments section
        if extraction.arguments:
            args_text = f"Prosecution Arguments: {extraction.arguments.prosecution}\n\n"
            args_text += f"Defence Arguments: {extraction.arguments.defence}"
            sections.append(CaseSection(
                section_name="Arguments",
                sequence_number=2,
                text=args_text
            ))
        
        # Reasoning section
        if extraction.reasoning:
            reasoning_text = f"Analysis: {extraction.reasoning.analysis_of_evidence}\n\n"
            reasoning_text += f"Legal Principles: {extraction.reasoning.legal_principles_applied}\n\n"
            reasoning_text += f"Court Findings: {extraction.reasoning.court_findings}"
            sections.append(CaseSection(
                section_name="Reasoning",
                sequence_number=3,
                text=reasoning_text
            ))
        
        # Judgement section
        if extraction.judgement:
            judgement_text = f"Decision: {extraction.judgement.final_decision}\n\n"
            judgement_text += f"Sentence: {extraction.judgement.sentence_or_bail_conditions}\n\n"
            judgement_text += f"Directions: {extraction.judgement.directions}"
            sections.append(CaseSection(
                section_name="Judgement",
                sequence_number=4,
                text=judgement_text
            ))
        
        return sections
    
    def _create_template_facts_section(self, template_facts: Dict[str, Any]) -> CaseSection:
        """
        Create a CaseSection from template-specific facts.
        
        Args:
            template_facts: Dictionary with template_id, template_schema, and extracted_facts
            
        Returns:
            CaseSection object with formatted template facts
        """
        import json
        
        template_id = template_facts.get('template_id', 'Unknown')
        extracted_facts = template_facts.get('extracted_facts', {})
        
        # Format the template facts as readable text
        facts_text = f"Template: {template_id}\n\n"
        
        # Convert extracted facts to formatted text
        for key, value in extracted_facts.items():
            if isinstance(value, dict):
                facts_text += f"{key.upper()}:\n"
                for sub_key, sub_value in value.items():
                    if isinstance(sub_value, list):
                        facts_text += f"  {sub_key}: {', '.join(str(v) for v in sub_value)}\n"
                    else:
                        facts_text += f"  {sub_key}: {sub_value}\n"
                facts_text += "\n"
            elif isinstance(value, list):
                facts_text += f"{key}: {', '.join(str(v) for v in value)}\n"
            else:
                facts_text += f"{key}: {value}\n"
        
        return CaseSection(
            section_name="Template Fact Extraction",
            sequence_number=5,
            text=facts_text
        )
    
    def ingest_single(
        self,
        file_path: Path,
        markdown_text: Optional[str] = None
    ) -> WeaviateIngestionResult:
        """
        Ingest a single PDF or markdown file into Weaviate.
        
        Args:
            file_path: Path to PDF or markdown file
            markdown_text: Optional pre-extracted markdown (if None, will extract from PDF)
            
        Returns:
            WeaviateIngestionResult with ingestion status and statistics
        """
        file_path = Path(file_path)
        logger.info(f"Starting ingestion for: {file_path.name}")
        
        try:
            # Stage 1: Get markdown content
            if markdown_text is None:
                if file_path.suffix.lower() == '.pdf':
                    # Use intelligent PDF extraction with fallback
                    markdown_text = self.pdf_extraction_service.extract(file_path)
                    logger.info(f"Extracted markdown from PDF: {len(markdown_text)} chars")
                else:
                    markdown_text = file_path.read_text(encoding='utf-8')
                    logger.info(f"Loaded markdown from file: {len(markdown_text)} chars")
            
            # Stage 2: Normalize, hash, and store markdown
            md_hash, md_uri = self.markdown_service.save(markdown_text)
            file_id = self._generate_file_id(md_hash)
            logger.info(f"Markdown stored: hash={md_hash[:8]}..., file_id={file_id}")
            
            # Check if already ingested
            from weaviate.classes.query import Filter
            client = self.weaviate_client.client
            doc_collection = client.collections.get("CaseDocuments")
            
            existing = doc_collection.query.fetch_objects(
                filters=Filter.by_property("file_id").equal(file_id),
                limit=1
            )
            
            if existing.objects:
                logger.warning(f"Document already ingested: {file_id}")
                return WeaviateIngestionResult(
                    file_id=file_id,
                    md_hash=md_hash,
                    status="skipped",
                    message="Document already exists",
                    metadata=None,
                    sections_count=0,
                    chunks_count=0
                )
            
            # Stage 3: Chunk text
            chunks = self.chunking_service.chunk_text(markdown_text)
            logger.info(f"Created {len(chunks)} chunks")
            
            # Stage 4a: summary_extraction - Extract comprehensive summary from markdown
            logger.info("Stage 4a: Extracting comprehensive summary from markdown...")
            extraction = self.extraction_service.summary_extraction(markdown_text)
            metadata = extraction.metadata
            
            # Create sections from comprehensive extraction
            sections = self._create_sections_from_extraction(extraction)
            logger.info(f"Summary extraction complete: {len(sections)} sections created")
            
            # Stage 4b: template_fact_extraction - Extract template-specific facts from summary
            logger.info("Stage 4b: Extracting template-specific facts from summary...")
            template_facts = self.extraction_service.template_fact_extraction(extraction)
            
            if template_facts:
                logger.info(f"Template fact extraction complete: {template_facts['template_id']}")
                logger.info(f"Extracted facts structure: {list(template_facts['extracted_facts'].keys())}")
                
                # Create a section for template facts
                template_facts_section = self._create_template_facts_section(template_facts)
                sections.append(template_facts_section)
                logger.info(f"Added template facts as section (total sections: {len(sections)})")
            else:
                logger.warning("No template facts extracted (no matching template found)")
            
            # Stage 5: Generate embeddings
            # Sections (including template facts section if present)
            section_texts = [s.text for s in sections]
            section_embeddings = self.embedding_service.embed_batch(section_texts, normalize=True)
            
            # Add embeddings to sections
            for section, embedding in zip(sections, section_embeddings):
                section.vector = embedding
            
            # Chunks
            chunk_texts = [c.text for c in chunks]
            chunk_embeddings = self.embedding_service.embed_batch(chunk_texts, normalize=True)
            
            logger.info(f"Generated embeddings: {len(section_embeddings)} sections, {len(chunk_embeddings)} chunks")
            
            # Stage 6: Batch upsert to Weaviate (4 collections)
            timestamp = datetime.now(timezone.utc).isoformat()
            
            # 6.1: CaseDocuments collection
            doc_data = {
                "file_id": file_id,
                "md_hash": md_hash,
                "original_filename": file_path.name,
                "md_gcs_uri": md_uri,
                "created_at": timestamp,
                "page_count": 0  # Could extract from PDF metadata if needed
            }
            
            with doc_collection.batch.dynamic() as batch:
                batch.add_object(properties=doc_data, uuid=file_id)
            
            logger.info(f"Inserted into CaseDocuments: {file_id}")
            
            # 6.2: CaseMetadata collection
            metadata_collection = client.collections.get("CaseMetadata")
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
            
            with metadata_collection.batch.dynamic() as batch:
                batch.add_object(properties=metadata_data, uuid=metadata_id)
            
            logger.info(f"Inserted into CaseMetadata: {metadata_id}")
            
            # 6.3: CaseSections collection
            sections_collection = client.collections.get("CaseSections")
            
            with sections_collection.batch.dynamic() as batch:
                for section in sections:
                    section_id = self._generate_section_id(file_id, section.section_name)
                    section_data = {
                        "section_id": section_id,
                        "file_id": file_id,
                        "section_name": section.section_name,
                        "sequence_number": section.sequence_number,
                        "text": section.text
                    }
                    batch.add_object(
                        properties=section_data,
                        uuid=section_id,
                        vector=section.vector
                    )
            
            logger.info(f"Inserted {len(sections)} sections into CaseSections")
            
            # 6.4: CaseChunks collection
            chunks_collection = client.collections.get("CaseChunks")
            
            with chunks_collection.batch.dynamic() as batch:
                for chunk, embedding in zip(chunks, chunk_embeddings):
                    chunk_id = self._generate_chunk_id(file_id, chunk.chunk_index)
                    chunk_data = {
                        "chunk_id": chunk_id,
                        "file_id": file_id,
                        "chunk_index": chunk.chunk_index,
                        "text": chunk.text,
                        "token_count": chunk.token_count
                    }
                    batch.add_object(
                        properties=chunk_data,
                        uuid=chunk_id,
                        vector=embedding
                    )
            
            logger.info(f"Inserted {len(chunks)} chunks into CaseChunks")
            
            # Stage 7: Verification
            result = WeaviateIngestionResult(
                file_id=file_id,
                md_hash=md_hash,
                status="success",
                message=f"Ingested: {len(sections)} sections, {len(chunks)} chunks",
                metadata=metadata,
                sections_count=len(sections),
                chunks_count=len(chunks)
            )
            
            logger.info(f"✓ Ingestion complete: {file_path.name}")
            return result
            
        except Exception as e:
            logger.error(f"Ingestion failed for {file_path.name}: {str(e)}", exc_info=True)
            return WeaviateIngestionResult(
                file_id="",
                md_hash="",
                status="error",
                message=str(e),
                metadata=None,
                sections_count=0,
                chunks_count=0
            )
    
    def ingest_batch(
        self,
        file_paths: List[Path],
        skip_existing: bool = True
    ) -> List[WeaviateIngestionResult]:
        """
        Ingest multiple files in batch.
        
        Args:
            file_paths: List of file paths to ingest
            skip_existing: Skip files that are already ingested
            
        Returns:
            List of ingestion results
        """
        results = []
        
        for i, file_path in enumerate(file_paths, 1):
            logger.info(f"Processing file {i}/{len(file_paths)}: {file_path.name}")
            result = self.ingest_single(file_path)
            results.append(result)
        
        # Summary statistics
        success_count = sum(1 for r in results if r.status == "success")
        skipped_count = sum(1 for r in results if r.status == "skipped")
        error_count = sum(1 for r in results if r.status == "error")
        
        logger.info(f"Batch ingestion complete: {success_count} success, {skipped_count} skipped, {error_count} errors")
        
        return results
    
    def verify_ingestion(self, file_id: str) -> Dict[str, int]:
        """
        Verify ingestion by counting objects across all collections.
        
        Args:
            file_id: File ID to verify
            
        Returns:
            Dictionary with counts per collection
        """
        client = self.weaviate_client.client
        
        counts = {
            "documents": 0,
            "metadata": 0,
            "sections": 0,
            "chunks": 0
        }
        
        # Count in each collection
        doc_collection = client.collections.get("CaseDocuments")
        doc_result = doc_collection.query.fetch_objects(
            filters={"path": ["file_id"], "operator": "Equal", "valueText": file_id},
            limit=1
        )
        counts["documents"] = len(doc_result.objects)
        
        metadata_collection = client.collections.get("CaseMetadata")
        metadata_result = metadata_collection.query.fetch_objects(
            filters={"path": ["file_id"], "operator": "Equal", "valueText": file_id},
            limit=1
        )
        counts["metadata"] = len(metadata_result.objects)
        
        sections_collection = client.collections.get("CaseSections")
        sections_result = sections_collection.aggregate.over_all(
            filters={"path": ["file_id"], "operator": "Equal", "valueText": file_id}
        )
        counts["sections"] = sections_result.total_count
        
        chunks_collection = client.collections.get("CaseChunks")
        chunks_result = chunks_collection.aggregate.over_all(
            filters={"path": ["file_id"], "operator": "Equal", "valueText": file_id}
        )
        counts["chunks"] = chunks_result.total_count
        
        logger.info(f"Verification for {file_id}: {counts}")
        return counts
    
    def close(self):
        """Close all connections and cleanup resources."""
        self.weaviate_client.close()
        logger.info("Pipeline closed")
