"""
Stage 4a: Summary Extractor
Haystack component for comprehensive summary extraction using main_template.json.
"""

from typing import List, Dict, Any, Optional
import logging

from haystack import component, Document

from src.services.extraction_service import ExtractionService
from src.core.config import Config

logger = logging.getLogger(__name__)


@component
class SummaryExtractor:
    """
    Haystack component for comprehensive summary extraction.
    Extracts metadata, case_facts, evidence, arguments, reasoning, judgement.
    
    Inputs:
        - documents (List[Document]): Haystack documents with markdown content
        - chunks (List[Dict]): Text chunks (passed through)
    
    Outputs:
        - documents (List[Document]): Original documents with extraction added to meta
        - chunks (List[Dict]): Text chunks (passed through unchanged)
        - extractions (List[Dict]): Comprehensive extractions (ComprehensiveExtraction as dict)
    """
    
    def __init__(self, config: Optional[Config] = None):
        """Initialize summary extractor."""
        self.extraction_service = ExtractionService(config=config)
        logger.info("SummaryExtractor initialized")
    
    @component.output_types(
        documents=List[Document],
        chunks=List[Dict[str, Any]],
        extractions=List[Dict[str, Any]]
    )
    def run(
        self,
        documents: List[Document],
        chunks: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Extract comprehensive summaries from markdown.
        
        Args:
            documents: List of Haystack documents
            chunks: Text chunks (passed through)
            
        Returns:
            Dictionary with 'documents', 'chunks', and 'extractions' keys
        """
        extractions = []
        
        for doc in documents:
            # Skip error documents
            if "error" in doc.meta:
                continue
            
            try:
                # Stage 4a: summary_extraction
                extraction = self.extraction_service.summary_extraction(doc.content)
                
                # Add extraction to document metadata
                doc.meta["extraction"] = extraction
                doc.meta["most_appropriate_section"] = extraction.metadata.most_appropriate_section
                
                # Convert to dict for output
                extraction_dict = extraction.to_dict()
                extraction_dict["file_id"] = doc.meta.get("file_id", "")
                extraction_dict["original_filename"] = doc.meta["original_filename"]
                extractions.append(extraction_dict)
                
                case_title = extraction.metadata.case_title or "Unknown"
                logger.info(f"✓ Extracted summary for {case_title}")
                logger.info(f"  Most appropriate section: {extraction.metadata.most_appropriate_section}")
                
            except Exception as e:
                logger.error(f"Failed to extract summary from {doc.meta.get('original_filename', 'unknown')}: {e}")
        
        return {
            "documents": documents,
            "chunks": chunks,
            "extractions": extractions
        }
