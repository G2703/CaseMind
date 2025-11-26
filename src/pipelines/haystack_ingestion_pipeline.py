"""
Pure Haystack-based ingestion pipeline using native components.
No wrappers - uses Haystack's LLMMetadataExtractor, embedders, and document store directly.
"""

import logging
import hashlib
import sys
import os
import json
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime

from haystack import Pipeline, Document
from haystack.components.extractors import LLMMetadataExtractor
from haystack.components.generators.chat import OpenAIChatGenerator
from haystack_integrations.document_stores.pgvector import PgvectorDocumentStore
from haystack.utils import Secret

from core.config import Config
from core.models import IngestResult, ProcessingStatus, CaseMetadata
from pipelines.haystack_custom_nodes import (
    MarkdownSaverNode
)
from pipelines.haystack_custom_nodes_v2 import (
    SummaryPostProcessorNode, MultiSectionEmbedderNode, TemplateSelectorNode,
    FactsExtractorNodeV2, FactsEmbedderNode, LegalCaseDBWriterNode,
    LegalCasesDuplicateCheckNode
)
from utils.convert_pdf_to_md import PDFToMarkdownConverter

logger = logging.getLogger(__name__)


class HaystackIngestionPipeline:
    """
    Pure Haystack ingestion pipeline for legal case PDFs.
    Uses native Haystack components without wrappers.
    """
    
    def __init__(self):
        """Initialize the Haystack ingestion pipeline."""
        self.config = Config()
        self.pipeline = Pipeline()
        self._current_pipeline_mode = None  # Track current pipeline mode
        
        # Initialize PDF converter
        config_dict = {
            'processing_settings': {
                'save_markdown_files': True,
                'markdown_output_dir': 'cases/markdown'
            }
        }
        self.pdf_converter = PDFToMarkdownConverter(config_dict)
        
        # Initialize document store
        self.document_store = self._init_document_store()
        
        # Build the pipeline (default with DB storage)
        self._build_pipeline(store_in_db=True)
        
        logger.info("HaystackIngestionPipeline initialized")
    
    def _init_document_store(self) -> PgvectorDocumentStore:
        """Initialize PgvectorDocumentStore and create legal_cases table."""
        host = self.config.db_host
        port = self.config.db_port
        user = self.config.db_user
        password = self.config.db_password
        database = self.config.db_name
        
        conn_str = f"postgresql://{user}:{password}@{host}:{port}/{database}"
        
        # Create legal_cases table if it doesn't exist
        self._create_legal_cases_table(conn_str)
        
        store = PgvectorDocumentStore(
            connection_string=Secret.from_token(conn_str),
            table_name="haystack_documents",
            embedding_dimension=768,
            vector_function="cosine_similarity",
            recreate_table=False,
            search_strategy="exact_nearest_neighbor",
            hnsw_recreate_index_if_exists=False,
            hnsw_index_creation_kwargs={
                "m": 16,
                "ef_construction": 64
            }
        )
        
        logger.info("PgvectorDocumentStore initialized")
        return store
    
    def _create_legal_cases_table(self, conn_str: str):
        """Create legal_cases table with multi-field embeddings."""
        import psycopg2
        
        try:
            conn = psycopg2.connect(conn_str)
            cursor = conn.cursor()
            
            # Create legal_cases table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS legal_cases (
                    file_id VARCHAR PRIMARY KEY,
                    case_id VARCHAR,
                    case_title VARCHAR,
                    file_hash VARCHAR UNIQUE,
                    original_filename VARCHAR,
                    ingestion_timestamp TIMESTAMP,
                    
                    -- Phase 1: Case summarization
                    summary JSONB,
                    
                    -- Phase 1: Section-wise embeddings
                    metadata_embedding vector(768),
                    case_facts_embedding vector(768),
                    issues_embedding vector(768),
                    evidence_embedding vector(768),
                    arguments_embedding vector(768),
                    reasoning_embedding vector(768),
                    judgement_embedding vector(768),
                    
                    -- Phase 3: Template-based fact extraction
                    factual_summary JSONB,
                    facts_embedding vector(768)
                );
                
                -- Create index on file_hash for duplicate detection
                CREATE INDEX IF NOT EXISTS idx_legal_cases_file_hash ON legal_cases(file_hash);
                
                -- Create index on facts_embedding for similarity search
                CREATE INDEX IF NOT EXISTS idx_legal_cases_facts_embedding 
                ON legal_cases USING hnsw (facts_embedding vector_cosine_ops);
            """)
            
            conn.commit()
            cursor.close()
            conn.close()
            
            logger.info("legal_cases table created/verified successfully")
            
        except Exception as e:
            logger.error(f"Failed to create legal_cases table: {e}")
            raise
    
    def _create_case_summarization_prompt(self) -> str:
        """Create comprehensive prompt for case summarization."""
        prompt = """Extract structured information from this Indian legal judgment. Return ONLY valid JSON.

{{ document.content }}

EXTRACTION SCHEMA & RULES:

1. METADATA
Extract: case_number, case_title, court_name, judgment_date, parties, counsel, judges_coram, case_type, citation, acts_and_sections
- sections_invoked: ALL mentioned sections ["IPC 376", "POCSO 6", "CrPC 482"]
- most_appropriate_section: PRIMARY offense section (consider severity & centrality)
- lower_court_history: trial_court_verdict, high_court_verdict
Missing required → "Unknown" | Missing optional → "" or []

2. CASE_FACTS (paragraphs, NOT bullets)
- prosecution_version: What prosecution alleges
- defence_version: Defence stance (empty if not recorded)
- timeline_of_events: Chronological list (empty if unavailable)
- incident_location, motive_alleged
NO inference. Extract only stated facts.

3. ISSUES_FOR_DETERMINATION
List of court-framed questions. If none explicit, infer neutrally: ["Whether accused entitled to bail?"]

4. EVIDENCE (all fields required, may be empty)
- witness_testimonies: [{witness_id, name, role, summary}] or []
- medical_evidence: Injuries, post-mortem, MLC (paragraph or "")
- forensic_evidence: FSL, DNA, ballistics (paragraph or "")
- documentary_evidence: List of exhibits or []
- recovery_and_seizure: Weapons, contraband (paragraph or "")
- expert_opinions, investigation_findings (paragraph or "")
Empty → "" or []. Never "Unknown".

5. ARGUMENTS
- prosecution: Paragraph or ""
- defence: Paragraph or ""

6. REASONING (paragraphs)
- analysis_of_evidence: Court's evaluation
- credibility_assessment: Witness reliability
- legal_principles_applied: Precedents, statutory interpretation
- circumstantial_chain: If applicable, else ""
- court_findings: Core findings
Empty → "". Extract only judgment content.

7. JUDGEMENT
- final_decision: Appeal allowed/bail granted/conviction upheld
- sentence_or_bail_conditions, directions
Empty → ""

JSON OUTPUT:
{
  "metadata": {
    "case_number": null, "case_title": "", "court_name": "", "judgment_date": "",
    "appellant_or_petitioner": null, "respondent": null, "judges_coram": null,
    "counsel_for_appellant": null, "counsel_for_respondent": null,
    "sections_invoked": [], "most_appropriate_section": "",
    "case_type": null, "citation": null, "acts_and_sections": null,
    "lower_court_history": {"trial_court_verdict": "", "high_court_verdict": ""}
  },
  "case_facts": {
    "prosecution_version": "", "defence_version": "",
    "timeline_of_events": [], "incident_location": "", "motive_alleged": ""
  },
  "issues_for_determination": [],
  "evidence": {
    "witness_testimonies": [],
    "medical_evidence": "", "forensic_evidence": "",
    "documentary_evidence": [], "recovery_and_seizure": "",
    "expert_opinions": "", "investigation_findings": ""
  },
  "arguments": {"prosecution": "", "defence": ""},
  "reasoning": {
    "analysis_of_evidence": "", "credibility_assessment": "",
    "legal_principles_applied": "", "circumstantial_chain": "", "court_findings": ""
  },
  "judgement": {"final_decision": "", "sentence_or_bail_conditions": "", "directions": ""}
}"""
        return prompt
    
    def _build_pipeline(self, store_in_db: bool = True):
        """
        Build the optimized Haystack pipeline with comprehensive summarization.
        
        Args:
            store_in_db: Whether to include duplicate check and database write nodes
        """
        
        # Check if we need to rebuild
        if self._current_pipeline_mode == store_in_db:
            logger.debug(f"Pipeline already configured for store_in_db={store_in_db}, skipping rebuild")
            return
        
        # Create a fresh pipeline
        self.pipeline = Pipeline()
        self._current_pipeline_mode = store_in_db
        
        logger.info(f"Building pipeline with store_in_db={store_in_db}")
        
        # 1. Case Summarizer (LLMMetadataExtractor with comprehensive prompt)
        summarization_prompt = self._create_case_summarization_prompt()
        chat_generator = OpenAIChatGenerator(
            api_key=Secret.from_token(self.config.openai_api_key),
            model="gpt-4o-2024-08-06",
            generation_kwargs={
                "response_format": {"type": "json_object"},
                "temperature": 0.5,
                "max_tokens": 8192  # Increased for comprehensive output
            }
        )
        
        case_summarizer = LLMMetadataExtractor(
            chat_generator=chat_generator,
            prompt=summarization_prompt,
            expected_keys=[
                "metadata", "case_facts", "issues_for_determination",
                "evidence", "arguments", "reasoning", "judgement"
            ],
            raise_on_failure=False
        )
        
        # 2. Markdown Saver
        markdown_saver = MarkdownSaverNode(output_dir="cases/markdown")
        
        # 3. Duplicate Checker (only if storing in DB)
        duplicate_checker = None
        if store_in_db:
            db_config = {
                "host": self.config.db_host,
                "port": self.config.db_port,
                "user": self.config.db_user,
                "password": self.config.db_password,
                "database": self.config.db_name
            }
            duplicate_checker = LegalCasesDuplicateCheckNode(db_config=db_config)
        
        # 4. Summary Post-Processor
        summary_processor = SummaryPostProcessorNode()
        
        # 5. Multi-Section Embedder (creates 7 embeddings from summary)
        section_embedder = MultiSectionEmbedderNode(model="sentence-transformers/all-mpnet-base-v2")
        
        # 6. Template Selector
        template_selector = TemplateSelectorNode(templates_dir=str(self.config.templates_dir))
        
        # 7. Facts Extractor (optimized - uses only case_facts + evidence)
        facts_extractor = FactsExtractorNodeV2(api_key=self.config.openai_api_key)
        
        # 8. Facts Embedder (creates primary search embedding)
        facts_embedder = FactsEmbedderNode(model="sentence-transformers/all-mpnet-base-v2")
        
        # 9. Database Writer (only if storing in DB)
        db_writer = None
        if store_in_db:
            db_writer = LegalCaseDBWriterNode(db_config=db_config)
        
        # Add components to pipeline
        self.pipeline.add_component("case_summarizer", case_summarizer)
        self.pipeline.add_component("markdown_saver", markdown_saver)
        if store_in_db and duplicate_checker:
            self.pipeline.add_component("duplicate_checker", duplicate_checker)
        self.pipeline.add_component("summary_processor", summary_processor)
        self.pipeline.add_component("section_embedder", section_embedder)
        self.pipeline.add_component("template_selector", template_selector)
        self.pipeline.add_component("facts_extractor", facts_extractor)
        self.pipeline.add_component("facts_embedder", facts_embedder)
        if store_in_db and db_writer:
            self.pipeline.add_component("db_writer", db_writer)
        
        # Connect components based on store_in_db flag
        self.pipeline.connect("case_summarizer.documents", "markdown_saver.documents")
        
        if store_in_db:
            # Full pipeline with duplicate check and database write
            self.pipeline.connect("markdown_saver.documents", "duplicate_checker.documents")
            self.pipeline.connect("duplicate_checker.documents", "summary_processor.documents")
        else:
            # In-memory pipeline without duplicate check
            self.pipeline.connect("markdown_saver.documents", "summary_processor.documents")
        
        self.pipeline.connect("summary_processor.documents", "section_embedder.documents")
        self.pipeline.connect("section_embedder.documents", "template_selector.documents")
        self.pipeline.connect("template_selector.documents", "facts_extractor.documents")
        self.pipeline.connect("template_selector.template", "facts_extractor.template")
        self.pipeline.connect("facts_extractor.documents", "facts_embedder.documents")
        
        if store_in_db:
            # Connect to database writer
            self.pipeline.connect("facts_embedder.documents", "db_writer.documents")
        
        logger.info(f"Pipeline built successfully (store_in_db={store_in_db})")
    
    def _compute_file_hash(self, file_path: Path) -> str:
        """Compute SHA-256 hash of file."""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    
    async def ingest_single(self, file_path: Path, display_summary: bool = True, store_in_db: bool = True) -> IngestResult:
        """
        Ingest a single PDF file through the Haystack pipeline.
        
        Args:
            file_path: Path to PDF file
            display_summary: Whether to display summary (for CLI)
            store_in_db: Whether to store in database (False for search-only mode)
            
        Returns:
            IngestResult with processing details and embeddings
        """
        file_path = Path(file_path)
        logger.info(f"Starting ingestion for: {file_path.name} (store_in_db={store_in_db})")
        
        try:
            # Rebuild pipeline based on store_in_db flag
            self._build_pipeline(store_in_db=store_in_db)
            
            # Step 1: Convert PDF to markdown
            logger.info(f"Converting PDF to markdown: {file_path.name}")
            raw_text = self.pdf_converter.extract_text_from_pdf(str(file_path))
            markdown_text = self.pdf_converter.clean_text(raw_text)
            
            # Step 2: Compute file hash
            file_hash = self._compute_file_hash(file_path)
            
            # Step 3: Create Haystack Document
            doc = Document(
                content=markdown_text,
                meta={
                    "original_filename": file_path.name,
                    "original_file_path": str(file_path),
                    "file_hash": file_hash,
                    "ingestion_timestamp": datetime.now().isoformat(),
                    "ingestion_method": "haystack_pipeline"
                }
            )
            
            # Step 4: Run optimized pipeline
            logger.info("Running optimized Haystack pipeline...")
            result = self.pipeline.run({"case_summarizer": {"documents": [doc]}})
            
            # Debug: Log all result keys
            logger.info(f"Pipeline result keys: {list(result.keys())}")
            for key in result.keys():
                output = result[key]
                if isinstance(output, dict):
                    logger.info(f"  {key}: {list(output.keys())}")
            
            # Extract results based on store_in_db mode
            if store_in_db:
                # Check for duplicates (only when storing)
                duplicate_status = result.get("duplicate_checker", {}).get("is_duplicate", False)
                existing_case = result.get("duplicate_checker", {}).get("existing_case", None)
                
                if duplicate_status and existing_case:
                    logger.warning("Document is a duplicate, returning existing case data")
                    
                    # Parse existing case metadata from summary JSON
                    summary_data = existing_case.get("summary", {})
                    metadata_dict = summary_data.get("metadata", {}) if summary_data else {}
                    
                    # Build metadata object with correct fields
                    metadata = CaseMetadata(
                        case_title=existing_case.get("case_title", "Unknown"),
                        court_name=metadata_dict.get("court_name", "Unknown"),
                        judgment_date=metadata_dict.get("judgment_date", "Unknown"),
                        sections_invoked=metadata_dict.get("sections_invoked", []),
                        most_appropriate_section=metadata_dict.get("most_appropriate_section", "Unknown"),
                        case_id=existing_case.get("case_id", "")
                    )
                    
                    # Extract facts summary from factual_summary JSON
                    factual_summary = existing_case.get("factual_summary", {})
                    facts_text = json.dumps(factual_summary) if factual_summary else ""
                    
                    return IngestResult(
                        case_id=existing_case.get("case_id", ""),
                        document_id=existing_case.get("file_id", ""),
                        status=ProcessingStatus.SKIPPED_DUPLICATE,
                        metadata=metadata,
                        facts_summary=facts_text,
                        file_hash=file_hash,
                        error_message="Duplicate document found in legal_cases table"
                    )
            
            # Check if fact extraction was successful
            fact_success = result.get("facts_extractor", {}).get("success", False)
            
            if not fact_success:
                logger.error("Fact extraction failed, rolling back")
                return IngestResult(
                    case_id="",
                    document_id="",
                    status=ProcessingStatus.FAILED,
                    metadata=None,
                    facts_summary="",
                    file_hash=file_hash,
                    error_message="Fact extraction failed"
                )
            
            # Get the final documents from the appropriate node
            if store_in_db:
                # Check if database write was successful
                db_success = result.get("db_writer", {}).get("success", False)
                
                if not db_success:
                    logger.error("Database write failed, rolling back")
                    return IngestResult(
                        case_id="",
                        document_id="",
                        status=ProcessingStatus.FAILED,
                        metadata=None,
                        facts_summary="",
                        file_hash=file_hash,
                        error_message="Database write failed"
                    )
                
                # Get the final document from db_writer
                final_docs = result.get("db_writer", {}).get("documents", [])
            else:
                # Get documents from facts_embedder (last node in in-memory mode)
                final_docs = result.get("facts_embedder", {}).get("documents", [])
            
            if not final_docs or len(final_docs) == 0:
                logger.error("No documents returned from pipeline")
                return IngestResult(
                    case_id="",
                    document_id="",
                    status=ProcessingStatus.FAILED,
                    metadata=None,
                    facts_summary="",
                    file_hash=file_hash,
                    error_message="No documents returned from pipeline"
                )
            
            # Get the final document
            final_doc = final_docs[0]
            
            # Extract metadata from summary
            summary = final_doc.meta.get("summary", {})
            metadata_dict = summary.get("metadata", {})
            factual_summary = final_doc.meta.get("factual_summary", {})
            
            # Generate facts summary from factual_summary for display
            facts_summary = json.dumps(factual_summary, indent=2) if factual_summary else "No facts extracted"
            
            # Create case ID
            case_id = metadata_dict.get("case_number", final_doc.id)
            
            # Create CaseMetadata object
            metadata = CaseMetadata(
                case_title=metadata_dict.get("case_title", "Unknown"),
                court_name=metadata_dict.get("court_name", "Unknown"),
                judgment_date=metadata_dict.get("judgment_date", "Unknown"),
                sections_invoked=metadata_dict.get("sections_invoked", []),
                most_appropriate_section=metadata_dict.get("most_appropriate_section", "Unknown"),
                case_id=case_id
            )
            
            # Extract embeddings from metadata (all 8 embeddings)
            import numpy as np
            embeddings = final_doc.meta.get("embeddings", {})
            
            logger.info(f"Successfully ingested case: {case_id} (store_in_db={store_in_db})")
            
            return IngestResult(
                case_id=case_id,
                document_id=final_doc.id,
                status=ProcessingStatus.COMPLETED,
                metadata=metadata,
                facts_summary=facts_summary,
                file_hash=file_hash,
                # Extract all embeddings for in-memory search
                embedding_facts=np.array(embeddings.get("facts_embedding")) if embeddings.get("facts_embedding") else None,
                embedding_metadata=np.array(embeddings.get("metadata_embedding")) if embeddings.get("metadata_embedding") else None,
                embedding_case_facts=np.array(embeddings.get("case_facts_embedding")) if embeddings.get("case_facts_embedding") else None,
                embedding_issues=np.array(embeddings.get("issues_embedding")) if embeddings.get("issues_embedding") else None,
                embedding_evidence=np.array(embeddings.get("evidence_embedding")) if embeddings.get("evidence_embedding") else None,
                embedding_arguments=np.array(embeddings.get("arguments_embedding")) if embeddings.get("arguments_embedding") else None,
                embedding_reasoning=np.array(embeddings.get("reasoning_embedding")) if embeddings.get("reasoning_embedding") else None,
                embedding_judgement=np.array(embeddings.get("judgement_embedding")) if embeddings.get("judgement_embedding") else None,
                error_message=None
            )
                
        except Exception as e:
            logger.error(f"Unexpected error during ingestion of {file_path.name}: {e}")
            return IngestResult(
                case_id="",
                document_id="",
                status=ProcessingStatus.FAILED,
                metadata=None,
                facts_summary="",
                file_hash=file_hash if 'file_hash' in locals() else None,
                error_message=str(e)
            )
    
    def count_legal_cases(self) -> int:
        """Count total cases in legal_cases table."""
        import psycopg2
        
        try:
            conn_str = (
                f"postgresql://{self.config.db_user}:{self.config.db_password}@"
                f"{self.config.db_host}:{self.config.db_port}/{self.config.db_name}"
            )
            conn = psycopg2.connect(conn_str)
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) FROM legal_cases;")
            count = cursor.fetchone()[0]
            
            cursor.close()
            conn.close()
            
            return count
        except Exception as e:
            logger.warning(f"Failed to count legal_cases: {e}")
            return 0
    
    def get_legal_cases_statistics(self) -> dict:
        """Get comprehensive statistics from legal_cases table."""
        import psycopg2
        
        try:
            conn_str = (
                f"postgresql://{self.config.db_user}:{self.config.db_password}@"
                f"{self.config.db_host}:{self.config.db_port}/{self.config.db_name}"
            )
            conn = psycopg2.connect(conn_str)
            cursor = conn.cursor()
            
            # Total cases
            cursor.execute("SELECT COUNT(*) FROM legal_cases;")
            total_cases = cursor.fetchone()[0]
            
            # Get oldest and newest cases
            cursor.execute("""
                SELECT 
                    MIN(ingestion_timestamp) as oldest,
                    MAX(ingestion_timestamp) as newest
                FROM legal_cases;
            """)
            oldest, newest = cursor.fetchone()
            
            # Get database size
            cursor.execute("""
                SELECT pg_size_pretty(pg_total_relation_size('legal_cases')) as size;
            """)
            db_size = cursor.fetchone()[0]
            
            # Count unique templates (based on most_appropriate_section from summary metadata)
            cursor.execute("""
                SELECT COUNT(DISTINCT summary->'metadata'->>'most_appropriate_section') 
                FROM legal_cases 
                WHERE summary IS NOT NULL;
            """)
            unique_templates = cursor.fetchone()[0] or 0
            
            cursor.close()
            conn.close()
            
            return {
                "total_documents": total_cases,
                "unique_templates": unique_templates,
                "oldest_case": oldest.strftime("%Y-%m-%d %H:%M") if oldest else "N/A",
                "newest_case": newest.strftime("%Y-%m-%d %H:%M") if newest else "N/A",
                "database_size": db_size if db_size else "N/A"
            }
        except Exception as e:
            logger.warning(f"Failed to get legal_cases statistics: {e}")
            return {
                "total_documents": 0,
                "unique_templates": 0,
                "oldest_case": "N/A",
                "newest_case": "N/A",
                "database_size": "N/A"
            }
    
    def visualize_pipeline(self) -> str:
        """Get pipeline visualization."""
        return self.pipeline.show()
