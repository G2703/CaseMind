"""
Stage 4b: Template Facts Extractor
Haystack component for template-specific fact extraction based on most_appropriate_section.
"""

from typing import List, Dict, Any, Optional
import logging

from haystack import component, Document

from src.services.extraction_service import ExtractionService
from src.core.config import Config

logger = logging.getLogger(__name__)


@component
class TemplateFactsExtractor:
    """
    Haystack component for template-specific fact extraction.
    Uses most_appropriate_section to load specific template.
    
    Inputs:
        - documents (List[Document]): Documents with extraction in meta
        - chunks (List[Dict]): Text chunks (passed through)
        - extractions (List[Dict]): Comprehensive extractions
    
    Outputs:
        - documents (List[Document]): Documents with template_facts added to meta
        - chunks (List[Dict]): Text chunks (passed through unchanged)
        - extractions (List[Dict]): Extractions (passed through unchanged)
        - sections (List[Dict]): Case sections including template facts section
    """
    
    def __init__(self, config: Optional[Config] = None):
        """Initialize template facts extractor."""
        self.extraction_service = ExtractionService(config=config)
        logger.info("TemplateFactsExtractor initialized")
    
    @component.output_types(
        documents=List[Document],
        chunks=List[Dict[str, Any]],
        extractions=List[Dict[str, Any]],
        sections=List[Dict[str, Any]]
    )
    def run(
        self,
        documents: List[Document],
        chunks: List[Dict[str, Any]],
        extractions: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Extract template-specific facts from summaries.
        
        Args:
            documents: List of Haystack documents with extraction in meta
            chunks: Text chunks (passed through)
            extractions: Comprehensive extractions
            
        Returns:
            Dictionary with 'documents', 'chunks', 'extractions', and 'sections' keys
        """
        all_sections = []
        
        for doc in documents:
            # Skip error documents
            if "error" in doc.meta:
                continue
            
            # Get extraction from document metadata
            extraction = doc.meta.get("extraction")
            if not extraction:
                logger.warning(f"No extraction found for {doc.meta.get('original_filename', 'unknown')}")
                continue
            
            file_id = doc.meta.get("file_id", "")
            
            try:
                # Create sections from comprehensive extraction
                sections = self._create_sections_from_extraction(extraction, file_id)
                
                # Stage 4b: template_fact_extraction
                template_facts = self.extraction_service.template_fact_extraction(extraction)
                
                if template_facts:
                    template_id = template_facts['template_id']
                    logger.info(f"✓ Extracted template facts for {template_id}")
                    
                    # Create template facts section
                    template_section = self._create_template_facts_section(template_facts, file_id)
                    sections.append(template_section)
                    
                    # Add template facts to document metadata
                    doc.meta["template_facts"] = template_facts
                else:
                    logger.warning(f"No template facts extracted for {doc.meta['original_filename']}")
                
                # Add all sections to output
                all_sections.extend(sections)
                logger.info(f"✓ Created {len(sections)} sections for {doc.meta['original_filename']}")
                
            except Exception as e:
                logger.error(f"Failed to extract template facts from {doc.meta.get('original_filename', 'unknown')}: {e}")
                doc.meta["error"] = str(e)
                doc.meta["error_stage"] = "template_facts_extractor"
        
        return {
            "documents": documents,
            "chunks": chunks,
            "extractions": extractions,
            "sections": all_sections
        }
    
    def _create_sections_from_extraction(self, extraction, file_id: str) -> List[Dict[str, Any]]:
        """Create CaseSection dictionaries from ComprehensiveExtraction."""
        sections = []
        
        # Case Facts section
        if extraction.case_facts and extraction.case_facts.prosecution_version:
            sections.append({
                "section_name": "Case Facts",
                "sequence_number": 0,
                "text": f"Prosecution: {extraction.case_facts.prosecution_version}\n\nDefence: {extraction.case_facts.defence_version}",
                "file_id": file_id
            })
        
        # Evidence section
        if extraction.evidence:
            evidence_text = f"Medical Evidence: {extraction.evidence.medical_evidence}\n\n"
            evidence_text += f"Forensic Evidence: {extraction.evidence.forensic_evidence}\n\n"
            evidence_text += f"Investigation: {extraction.evidence.investigation_findings}"
            sections.append({
                "section_name": "Evidence",
                "sequence_number": 1,
                "text": evidence_text,
                "file_id": file_id
            })
        
        # Arguments section
        if extraction.arguments:
            args_text = f"Prosecution Arguments: {extraction.arguments.prosecution}\n\n"
            args_text += f"Defence Arguments: {extraction.arguments.defence}"
            sections.append({
                "section_name": "Arguments",
                "sequence_number": 2,
                "text": args_text,
                "file_id": file_id
            })
        
        # Reasoning section
        if extraction.reasoning:
            reasoning_text = f"Analysis: {extraction.reasoning.analysis_of_evidence}\n\n"
            reasoning_text += f"Legal Principles: {extraction.reasoning.legal_principles_applied}\n\n"
            reasoning_text += f"Court Findings: {extraction.reasoning.court_findings}"
            sections.append({
                "section_name": "Reasoning",
                "sequence_number": 3,
                "text": reasoning_text,
                "file_id": file_id
            })
        
        # Judgement section
        if extraction.judgement:
            judgement_text = f"Decision: {extraction.judgement.final_decision}\n\n"
            judgement_text += f"Sentence: {extraction.judgement.sentence_or_bail_conditions}\n\n"
            judgement_text += f"Directions: {extraction.judgement.directions}"
            sections.append({
                "section_name": "Judgement",
                "sequence_number": 4,
                "text": judgement_text,
                "file_id": file_id
            })
        
        return sections
    
    def _create_template_facts_section(self, template_facts: Dict[str, Any], file_id: str) -> Dict[str, Any]:
        """Create a section dictionary from template-specific facts."""
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
        
        return {
            "section_name": "template_Fact_extraction",
            "sequence_number": 5,
            "text": facts_text,
            "file_id": file_id
        }
