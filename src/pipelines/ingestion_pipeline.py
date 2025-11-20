"""
Data ingestion pipeline for processing and storing legal cases.
Supports both single file and batch folder processing.
"""

import logging
from typing import List
from pathlib import Path
from datetime import datetime

from core.models import (
    IngestResult, BatchIngestResult, ProcessingStatus,
    CaseMetadata, ExtractedFacts, Document
)
from core.exceptions import DocumentLoadError, MetadataExtractionError, FactExtractionError
from services.pdf_loader import PDFLoader
from services.metadata_extractor import MetadataExtractor
from services.template_selector import TemplateSelector
from services.fact_extractor import FactExtractor
from services.embedding_service import EmbeddingService
from services.duplicate_checker import DuplicateChecker
from infrastructure.document_store import PGVectorDocumentStore
from utils.helpers import compute_file_hash, generate_case_id
from core.config import Config

# Import PDF to Markdown converter from raw_code
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'raw_code', 'bg_creation'))
from convert_pdf_to_md import PDFToMarkdownConverter

logger = logging.getLogger(__name__)


class DataIngestionPipeline:
    """
    Orchestrates the data ingestion process (Steps 5-11).
    Facade pattern simplifying complex ingestion workflow.
    """
    
    def __init__(self):
        """Initialize all pipeline components."""
        # Load config for PDF converter settings
        config = Config()
        config_dict = {
            'processing_settings': {
                'save_markdown_files': True,
                'markdown_output_dir': 'cases/markdown'
            }
        }
        
        self.pdf_converter = PDFToMarkdownConverter(config_dict)
        self.pdf_loader = PDFLoader()
        self.metadata_extractor = MetadataExtractor()
        self.template_selector = TemplateSelector()
        self.fact_extractor = FactExtractor()
        self.embedder = EmbeddingService()
        self.store = PGVectorDocumentStore()
        self.duplicate_checker = DuplicateChecker(self.store)
        
        logger.info("Data ingestion pipeline initialized")
    
    async def ingest_single(
        self, 
        file_path: Path, 
        display_summary: bool = True
    ) -> IngestResult:
        """
        Ingest a single PDF file.
        
        Args:
            file_path: Path to PDF file
            display_summary: Whether to display summary (for CLI)
            
        Returns:
            IngestResult with processing details
        """
        file_path = Path(file_path)
        logger.info(f"Starting ingestion for: {file_path.name}")
        
        try:
            # Step 5a: Convert PDF to Markdown
            logger.info(f"Converting PDF to markdown: {file_path.name}")
            raw_text = self.pdf_converter.extract_text_from_pdf(str(file_path))
            markdown_text = self.pdf_converter.clean_text(raw_text)
            
            # Step 5b: Load PDF (for validation and fallback)
            # self.pdf_loader.load(file_path)
            
            # Step 6: Extract metadata from markdown
            metadata_dict = await self.metadata_extractor.extract(markdown_text, file_path)
            
            # Generate case ID
            case_id = generate_case_id(metadata_dict)
            metadata_dict['case_id'] = case_id
            
            metadata = CaseMetadata(**{
                k: metadata_dict[k] for k in [
                    'case_title', 'court_name', 'judgment_date',
                    'sections_invoked', 'most_appropriate_section', 'case_id'
                ]
            })
            
            # Step 7: Select template
            template = self.template_selector.select(metadata_dict)
            
            # Step 8: Extract facts from markdown
            facts_dict = await self.fact_extractor.extract(markdown_text, template)
            facts = ExtractedFacts(**facts_dict)
            
            # Step 9: Generate facts summary
            facts_summary = facts.to_summary_text()
            
            # Step 10: Calculate dual embeddings
            complete_metadata = {
                **metadata_dict,
                'template_id': template.template_id,
                'template_label': template.label,
                'confidence_score': template.confidence_score,
                'extracted_facts': facts_dict,
                'facts_summary': facts_summary,
                'original_file_path': str(file_path),
                'original_filename': file_path.name,
                'ingestion_timestamp': datetime.now().isoformat(),
                'ingestion_method': 'single'
            }
            
            embeddings = self.embedder.embed_document_dual(facts_summary, complete_metadata)
            
            # Step 11: Store in database
            file_hash = compute_file_hash(file_path)
            document_id = case_id
            
            document_dict = {
                'id': document_id,
                'content': facts_summary,
                'content_type': 'text',
                'meta': complete_metadata,
                'embedding_facts': embeddings['embedding_facts'],
                'embedding_metadata': embeddings['embedding_metadata'],
                'file_hash': file_hash,
                'original_filename': file_path.name
            }
            
            stored_id = self.store.write_document(document_dict)
            
            if stored_id:
                logger.info(f"Successfully ingested case: {case_id}")
                status = ProcessingStatus.COMPLETED
            else:
                logger.warning(f"Case already exists (duplicate): {case_id}")
                status = ProcessingStatus.SKIPPED_DUPLICATE
            
            return IngestResult(
                case_id=case_id,
                document_id=document_id,
                status=status,
                metadata=metadata,
                facts_summary=facts_summary,
                embedding_facts=embeddings['embedding_facts'],
                embedding_metadata=embeddings['embedding_metadata'],
                error_message=None
            )
            
        except DocumentLoadError as e:
            logger.error(f"Document load failed for {file_path.name}: {e}")
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
        except (MetadataExtractionError, FactExtractionError) as e:
            logger.error(f"Extraction failed for {file_path.name}: {e}")
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
    
    async def process_batch(self, folder_path: Path) -> BatchIngestResult:
        """
        Process entire folder of PDF files with duplicate detection.
        
        Args:
            folder_path: Path to folder containing PDFs
            
        Returns:
            BatchIngestResult with statistics
        """
        folder_path = Path(folder_path)
        logger.info(f"Starting batch processing for folder: {folder_path}")
        
        if not folder_path.exists():
            raise FileNotFoundError(f"Folder not found: {folder_path}")
        
        # Find all PDF files
        pdf_files = list(folder_path.glob("*.pdf"))
        total_files = len(pdf_files)
        
        logger.info(f"Found {total_files} PDF files in folder")
        
        # Statistics
        processed = 0
        skipped_duplicates = 0
        failed = 0
        case_ids = []
        errors = []
        
        # Process each PDF
        for i, pdf_file in enumerate(pdf_files, 1):
            logger.info(f"Processing file {i}/{total_files}: {pdf_file.name}")
            
            try:
                # Check for duplicate
                duplicate_status = self.duplicate_checker.check(pdf_file)
                
                if duplicate_status.is_duplicate:
                    logger.info(f"Skipping duplicate: {pdf_file.name}")
                    skipped_duplicates += 1
                    continue
                
                # Ingest file
                result = await self.ingest_single(pdf_file, display_summary=False)
                
                if result.status == ProcessingStatus.COMPLETED:
                    processed += 1
                    case_ids.append(result.case_id)
                elif result.status == ProcessingStatus.SKIPPED_DUPLICATE:
                    skipped_duplicates += 1
                else:
                    failed += 1
                    errors.append(f"{pdf_file.name}: {result.error_message}")
                
            except Exception as e:
                logger.error(f"Error processing {pdf_file.name}: {e}")
                failed += 1
                errors.append(f"{pdf_file.name}: {str(e)}")
        
        logger.info(f"Batch processing completed: {processed} processed, "
                   f"{skipped_duplicates} skipped, {failed} failed")
        
        return BatchIngestResult(
            total_files=total_files,
            processed=processed,
            skipped_duplicates=skipped_duplicates,
            failed=failed,
            case_ids=case_ids,
            errors=errors
        )
