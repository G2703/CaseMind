"""
Pure Haystack-based ingestion pipeline using native components.
No wrappers - uses Haystack's LLMMetadataExtractor, embedders, and document store directly.
"""

import logging
import hashlib
import sys
import os
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
    MarkdownSaverNode, TemplateSaverNode, DuplicateCheckNode, 
    TemplateLoaderNode, FactExtractorNode, DualEmbedderNode
)

# Import PDF to Markdown converter
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'raw_code', 'bg_creation'))
from convert_pdf_to_md import PDFToMarkdownConverter

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
        
        # Build the pipeline
        self._build_pipeline()
        
        logger.info("HaystackIngestionPipeline initialized")
    
    def _init_document_store(self) -> PgvectorDocumentStore:
        """Initialize PgvectorDocumentStore."""
        host = self.config.db_host
        port = self.config.db_port
        user = self.config.db_user
        password = self.config.db_password
        database = self.config.db_name
        
        conn_str = f"postgresql://{user}:{password}@{host}:{port}/{database}"
        
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
    
    def _create_metadata_prompt(self) -> str:
        """Create prompt for metadata extraction."""
        prompt = """Analyze the following Indian legal case document and extract comprehensive metadata.

Legal Document Text:
{{ document.content }}

Extract the following metadata with high accuracy:
1. Case identification details (number, title, court)
2. Party information (appellant, respondent, counsel)
3. Judicial details (judges, dates)
4. Legal provisions (all sections invoked and the most appropriate one)
5. Case classification information

CRITICAL INSTRUCTIONS FOR SECTION IDENTIFICATION:

For sections_invoked:
- Extract ALL legal sections mentioned in the case (IPC, POCSO, CrPC, NDPS, etc.)
- Include sections from charges, arguments, and judicial discussion
- Format as list: ["IPC 376", "POCSO 6", "CrPC 482"]

For most_appropriate_section (MOST IMPORTANT):
- Analyze the entire case to identify which section represents the PRIMARY offense
- Consider severity: murder > rape > robbery > theft
- Consider centrality: the section most discussed in the judgment
- If multiple sections, choose the one with highest legal severity

Return a JSON object with these exact keys:
{
  "case_number": "string or null",
  "case_title": "string",
  "court_name": "string",
  "judgment_date": "string",
  "appellant_or_petitioner": "string or null",
  "respondent": "string or null",
  "judges_coram": "string or null",
  "counsel_for_appellant": "string or null",
  "counsel_for_respondent": "string or null",
  "sections_invoked": ["list of strings"],
  "most_appropriate_section": "string (e.g., 'IPC 376', 'IPC 302')",
  "case_type": "string or null",
  "citation": "string or null",
  "acts_and_sections": "string or null"
}

Use "Unknown" for missing required fields (case_title, court_name, judgment_date, most_appropriate_section).
Use null for optional fields if not found.
"""
        return prompt
    
    def _build_pipeline(self):
        """Build the Haystack pipeline with all components."""
        
        # 1. Metadata Extractor
        metadata_prompt = self._create_metadata_prompt()
        chat_generator = OpenAIChatGenerator(
            api_key=Secret.from_token(self.config.openai_api_key),
            model="gpt-4o-2024-08-06",
            generation_kwargs={
                "response_format": {"type": "json_object"},
                "temperature": 0.5,
                "max_tokens": 1024
            }
        )
        
        metadata_extractor = LLMMetadataExtractor(
            chat_generator=chat_generator,
            prompt=metadata_prompt,
            expected_keys=[
                "case_number", "case_title", "court_name", "judgment_date",
                "appellant_or_petitioner", "respondent", "judges_coram",
                "counsel_for_appellant", "counsel_for_respondent",
                "sections_invoked", "most_appropriate_section",
                "case_type", "citation", "acts_and_sections"
            ],
            raise_on_failure=False
        )
        
        # 2. Markdown Saver
        markdown_saver = MarkdownSaverNode(output_dir="cases/markdown")
        
        # 3. Duplicate Checker
        duplicate_checker = DuplicateCheckNode(document_store=self.document_store)
        
        # 4. Template Loader
        template_loader = TemplateLoaderNode(templates_dir=str(self.config.templates_dir))
        
        # 5. Fact Extractor
        fact_extractor = FactExtractorNode(api_key=self.config.openai_api_key)
        
        # 6. Template Saver
        template_saver = TemplateSaverNode(output_dir="cases/extracted")
        
        # 7. Dual Embedder (creates facts + metadata embeddings and stores to DB)
        dual_embedder = DualEmbedderNode(
            document_store=self.document_store,
            model="sentence-transformers/all-mpnet-base-v2"
        )
        
        # Add components to pipeline
        self.pipeline.add_component("metadata_extractor", metadata_extractor)
        self.pipeline.add_component("markdown_saver", markdown_saver)
        self.pipeline.add_component("duplicate_checker", duplicate_checker)
        self.pipeline.add_component("template_loader", template_loader)
        self.pipeline.add_component("fact_extractor", fact_extractor)
        self.pipeline.add_component("template_saver", template_saver)
        self.pipeline.add_component("dual_embedder", dual_embedder)
        
        # Connect components
        self.pipeline.connect("metadata_extractor.documents", "markdown_saver.documents")
        self.pipeline.connect("markdown_saver.documents", "duplicate_checker.documents")
        self.pipeline.connect("duplicate_checker.documents", "template_loader.documents")
        self.pipeline.connect("template_loader.documents", "fact_extractor.documents")
        self.pipeline.connect("template_loader.template", "fact_extractor.template")
        self.pipeline.connect("fact_extractor.documents", "template_saver.documents")
        self.pipeline.connect("template_saver.documents", "dual_embedder.documents")
        
        logger.info("Pipeline built successfully")
    
    def _compute_file_hash(self, file_path: Path) -> str:
        """Compute SHA-256 hash of file."""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    
    async def ingest_single(self, file_path: Path, display_summary: bool = True) -> IngestResult:
        """
        Ingest a single PDF file through the Haystack pipeline.
        
        Args:
            file_path: Path to PDF file
            display_summary: Whether to display summary (for CLI)
            
        Returns:
            IngestResult with processing details
        """
        file_path = Path(file_path)
        logger.info(f"Starting ingestion for: {file_path.name}")
        
        try:
            # Step 1: Convert PDF to Markdown
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
            
            # Step 4: Run pipeline
            logger.info("Running Haystack pipeline...")
            result = self.pipeline.run({"metadata_extractor": {"documents": [doc]}})
            
            # Debug: Log all result keys
            logger.info(f"Pipeline result keys: {list(result.keys())}")
            for key in result.keys():
                output = result[key]
                if isinstance(output, dict):
                    logger.info(f"  {key}: {list(output.keys())}")
            
            # Extract results
            duplicate_status = result.get("duplicate_checker", {}).get("is_duplicate", False)
            
            if duplicate_status:
                logger.warning("Document is a duplicate, retrieving existing data from database")
                
                # Retrieve existing document from database
                try:
                    import psycopg2
                    from psycopg2.extras import RealDictCursor
                    
                    conn_str = f"postgresql://{self.config.db_user}:{self.config.db_password}@{self.config.db_host}:{self.config.db_port}/{self.config.db_name}"
                    conn = psycopg2.connect(conn_str)
                    cursor = conn.cursor(cursor_factory=RealDictCursor)
                    
                    cursor.execute("""
                        SELECT id, content, meta 
                        FROM haystack_documents 
                        WHERE meta->>'file_hash' = %s
                        LIMIT 1
                    """, (file_hash,))
                    
                    existing = cursor.fetchone()
                    cursor.close()
                    conn.close()
                    
                    if existing:
                        meta = existing['meta'] or {}
                        metadata = CaseMetadata(
                            case_title=meta.get("case_title", "Unknown"),
                            court_name=meta.get("court_name", "Unknown"),
                            judgment_date=meta.get("judgment_date", "Unknown"),
                            sections_invoked=meta.get("sections_invoked", []),
                            most_appropriate_section=meta.get("most_appropriate_section", "Unknown"),
                            case_id=existing['id']
                        )
                        
                        return IngestResult(
                            case_id=existing['id'],
                            document_id=existing['id'],
                            status=ProcessingStatus.SKIPPED_DUPLICATE,
                            metadata=metadata,
                            facts_summary=existing['content'] or "",
                            embedding_facts=None,
                            embedding_metadata=None,
                            error_message=None
                        )
                    
                except Exception as e:
                    logger.error(f"Failed to retrieve duplicate document: {e}")
                
                # Fallback if database retrieval fails
                return IngestResult(
                    case_id="",
                    document_id="",
                    status=ProcessingStatus.SKIPPED_DUPLICATE,
                    metadata=None,
                    facts_summary="",
                    embedding_facts=None,
                    embedding_metadata=None,
                    error_message="Duplicate document"
                )
            
            # Check if fact extraction was successful
            fact_success = result.get("fact_extractor", {}).get("success", False)
            
            if not fact_success:
                logger.error("Fact extraction failed, document not ingested")
                return IngestResult(
                    case_id="",
                    document_id="",
                    status=ProcessingStatus.FAILED,
                    metadata=None,
                    facts_summary="",
                    embedding_facts=None,
                    embedding_metadata=None,
                    error_message="Fact extraction failed"
                )
            
            # Check if dual embedding was successful
            dual_embedder_docs = result.get("dual_embedder", {}).get("documents", [])
            
            if not dual_embedder_docs or len(dual_embedder_docs) == 0:
                logger.error("Dual embedding failed, document not stored")
                return IngestResult(
                    case_id="",
                    document_id="",
                    status=ProcessingStatus.FAILED,
                    metadata=None,
                    facts_summary="",
                    embedding_facts=None,
                    embedding_metadata=None,
                    error_message="Dual embedding failed"
                )
            
            # Get the embedded document (which has all metadata)
            embedded_doc = dual_embedder_docs[0]
            
            # Get facts summary from embedded document (DualEmbedderNode sets doc.content to facts_summary)
            facts_summary = embedded_doc.content if embedded_doc.content else ""
            
            # Also try to get from metadata if content is empty
            if not facts_summary or len(facts_summary.strip()) == 0:
                facts_summary = embedded_doc.meta.get("facts_summary", "")
            
            logger.info(f"Retrieved facts summary ({len(facts_summary)} chars)")
            
            # Extract metadata from the embedded document
            case_id = embedded_doc.meta.get("case_id", embedded_doc.id)
            metadata = CaseMetadata(
                case_title=embedded_doc.meta.get("case_title", "Unknown"),
                court_name=embedded_doc.meta.get("court_name", "Unknown"),
                judgment_date=embedded_doc.meta.get("judgment_date", "Unknown"),
                sections_invoked=embedded_doc.meta.get("sections_invoked", []),
                most_appropriate_section=embedded_doc.meta.get("most_appropriate_section", "Unknown"),
                case_id=case_id
            )
            
            logger.info(f"Successfully ingested case: {case_id}")
            
            return IngestResult(
                case_id=case_id,
                document_id=embedded_doc.id,
                status=ProcessingStatus.COMPLETED,
                metadata=metadata,
                facts_summary=facts_summary,
                embedding_facts=None,  # Stored in DB 'embedding' column
                embedding_metadata=None,  # Stored in DB 'embedding_metadata' column
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
                embedding_facts=None,
                embedding_metadata=None,
                error_message=str(e)
            )
    
    def visualize_pipeline(self) -> str:
        """Get pipeline visualization."""
        return self.pipeline.show()
