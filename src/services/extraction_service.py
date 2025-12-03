""" 
LLM extraction service - Two-stage extraction process.
Stage 1 (summary_extraction): Extract comprehensive summary using main_template.json
Stage 2 (template_fact_extraction): Extract template-specific facts using most_appropriate_section
"""

import json
import logging
from typing import Dict, Any, List, Optional, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from src.core.config import Config
from pathlib import Path
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from src.core.models import (
    ComprehensiveExtraction,
    WeaviateMetadata,
    CaseFacts,
    Evidence,
    Arguments,
    Reasoning,
    Judgement,
    WitnessTestimony,
    LowerCourtHistory
)

logger = logging.getLogger(__name__)


class ExtractionService:
    """
    Two-stage LLM extraction service:
    1. Extract comprehensive summary (main_template.json schema)
    2. Extract template-specific facts based on most_appropriate_section
    """
    
    def __init__(self, config: Optional['Config'] = None):
        """Initialize extraction service."""
        from src.core.config import Config
        self.config = config or Config()
        self._load_prompts()
        self._load_main_template()
        self._load_section_templates()
        
        # Import OpenAI here to avoid initialization errors
        from openai import OpenAI
        self.client = OpenAI(api_key=self.config.openai_api_key)
        
        logger.info("ExtractionService initialized (two-stage extraction)")
    
    def _load_prompts(self):
        """Load prompts from prompts.json."""
        prompts_path = self.config.prompts_path
        
        if not prompts_path.exists():
            raise FileNotFoundError(f"Prompts file not found: {prompts_path}")
        
        with open(prompts_path, 'r', encoding='utf-8') as f:
            prompts = json.load(f)
        
        self.metadata_prompt_template = prompts.get('metadata_extraction', '')
        self.template_fact_prompt = prompts.get('template_fact_extraction', '')
        
        logger.info("Loaded prompts from prompts.json")
    
    def _load_main_template(self):
        """Load main template for comprehensive extraction."""
        template_path = self.config.main_template_path
        
        if not template_path.exists():
            raise FileNotFoundError(f"Main template not found: {template_path}")
        
        with open(template_path, 'r', encoding='utf-8') as f:
            self.main_template = json.load(f)
        
        logger.info(f"Loaded main template v{self.main_template.get('version', '1.0')}")
    
    def _load_section_templates(self):
        """Load section-specific templates (IPC 302, 498A, etc.)."""
        templates_dir = Path("templates")
        self.section_templates = {}
        
        # Load all templates in templates directory
        if templates_dir.exists():
            for template_file in templates_dir.glob("*.json"):
                if template_file.name != "main_template.json" and template_file.name != "templates.json":
                    try:
                        with open(template_file, 'r', encoding='utf-8') as f:
                            template_data = json.load(f)
                            # Extract template ID from filename (e.g., ipc_302.json -> IPC 302)
                            template_id = template_file.stem.replace('_', ' ').upper()
                            self.section_templates[template_id] = template_data
                    except Exception as e:
                        logger.warning(f"Failed to load template {template_file.name}: {e}")
        
        logger.info(f"Loaded {len(self.section_templates)} section templates")
    
    def summary_extraction(self, markdown_text: str) -> ComprehensiveExtraction:
        """
        STAGE 1: Extract comprehensive summary using main_template.json schema.
        
        Args:
            markdown_text: Full markdown text of legal document
            
        Returns:
            ComprehensiveExtraction with all structured data
        """
        logger.info("Stage 1 (summary_extraction): Extracting comprehensive summary...")
        
        prompt = self.metadata_prompt_template.replace('{document_text}', markdown_text)
        
        try:
            # Call OpenAI API for comprehensive extraction
            response = self.client.chat.completions.create(
                model="gpt-4o-2024-08-06",
                messages=[
                    {"role": "system", "content": "You are a legal document analyzer specializing in Indian law. Extract structured information and return ONLY valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.2,
                max_tokens=8000
            )
            
            # Parse response
            content = response.choices[0].message.content
            data = json.loads(content)
            
            # Parse metadata section
            metadata_dict = data.get('metadata', {})
            lower_court = metadata_dict.get('lower_court_history', {})
            
            metadata = WeaviateMetadata(
                case_number=metadata_dict.get('case_number'),
                case_title=metadata_dict.get('case_title', ''),
                court_name=metadata_dict.get('court_name', ''),
                judgment_date=metadata_dict.get('judgment_date', ''),
                appellant_or_petitioner=metadata_dict.get('appellant_or_petitioner'),
                respondent=metadata_dict.get('respondent'),
                judges_coram=metadata_dict.get('judges_coram', []),
                counsel_for_appellant=metadata_dict.get('counsel_for_appellant'),
                counsel_for_respondent=metadata_dict.get('counsel_for_respondent'),
                sections_invoked=metadata_dict.get('sections_invoked', []),
                most_appropriate_section=metadata_dict.get('most_appropriate_section', ''),
                case_type=metadata_dict.get('case_type'),
                citation=metadata_dict.get('citation'),
                acts_and_sections=metadata_dict.get('acts_and_sections'),
                lower_court_history=LowerCourtHistory(
                    trial_court_verdict=lower_court.get('trial_court_verdict', ''),
                    high_court_verdict=lower_court.get('high_court_verdict', '')
                ) if lower_court else None
            )
            
            # Parse case_facts
            facts_dict = data.get('case_facts', {})
            case_facts = CaseFacts(
                prosecution_version=facts_dict.get('prosecution_version', ''),
                defence_version=facts_dict.get('defence_version', ''),
                timeline_of_events=facts_dict.get('timeline_of_events', []),
                incident_location=facts_dict.get('incident_location', ''),
                motive_alleged=facts_dict.get('motive_alleged', '')
            )
            
            # Parse issues
            issues = data.get('issues_for_determination', [])
            
            # Parse evidence
            evidence_dict = data.get('evidence', {})
            witness_list = []
            for w in evidence_dict.get('witness_testimonies', []):
                if isinstance(w, dict):
                    witness_list.append(WitnessTestimony(
                        witness_id=w.get('witness_id', ''),
                        name=w.get('name', ''),
                        role=w.get('role', ''),
                        summary=w.get('summary', '')
                    ))
            
            evidence = Evidence(
                witness_testimonies=witness_list,
                medical_evidence=evidence_dict.get('medical_evidence', ''),
                forensic_evidence=evidence_dict.get('forensic_evidence', ''),
                documentary_evidence=evidence_dict.get('documentary_evidence', []),
                recovery_and_seizure=evidence_dict.get('recovery_and_seizure', ''),
                expert_opinions=evidence_dict.get('expert_opinions', ''),
                investigation_findings=evidence_dict.get('investigation_findings', '')
            )
            
            # Parse arguments
            arguments_dict = data.get('arguments', {})
            arguments = Arguments(
                prosecution=arguments_dict.get('prosecution', ''),
                defence=arguments_dict.get('defence', '')
            )
            
            # Parse reasoning
            reasoning_dict = data.get('reasoning', {})
            reasoning = Reasoning(
                analysis_of_evidence=reasoning_dict.get('analysis_of_evidence', ''),
                credibility_assessment=reasoning_dict.get('credibility_assessment', ''),
                legal_principles_applied=reasoning_dict.get('legal_principles_applied', ''),
                circumstantial_chain=reasoning_dict.get('circumstantial_chain', ''),
                court_findings=reasoning_dict.get('court_findings', '')
            )
            
            # Parse judgement
            judgement_dict = data.get('judgement', {})
            judgement = Judgement(
                final_decision=judgement_dict.get('final_decision', ''),
                sentence_or_bail_conditions=judgement_dict.get('sentence_or_bail_conditions', ''),
                directions=judgement_dict.get('directions', '')
            )
            
            # Create comprehensive extraction
            extraction = ComprehensiveExtraction(
                metadata=metadata,
                case_facts=case_facts,
                issues_for_determination=issues,
                evidence=evidence,
                arguments=arguments,
                reasoning=reasoning,
                judgement=judgement
            )
            
            logger.info(f"Stage 1 (summary_extraction) complete: Extracted comprehensive summary for {metadata.case_title or 'Unknown'}")
            logger.info(f"Most appropriate section: {metadata.most_appropriate_section}")
            
            return extraction
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse comprehensive extraction response: {e}")
            return self._create_empty_extraction()
        except Exception as e:
            logger.error(f"Comprehensive extraction failed: {e}", exc_info=True)
            return self._create_empty_extraction()
    
    def template_fact_extraction(
        self,
        summary: ComprehensiveExtraction
    ) -> Optional[Dict[str, Any]]:
        """
        STAGE 2: Extract template-specific facts based on most_appropriate_section.
        Uses ONLY the comprehensive summary, NOT the original markdown document.
        
        Args:
            summary: Comprehensive extraction from Stage 1
            
        Returns:
            Template-specific extracted facts or None if template not found
        """
        most_appropriate = summary.metadata.most_appropriate_section
        
        if not most_appropriate:
            logger.warning("No most_appropriate_section found, skipping Stage 2 (template_fact_extraction)")
            return None
        
        # Normalize section name for template lookup - try both formats
        template_key_underscore = most_appropriate.upper().replace(' ', '_')
        template_key_space = most_appropriate.upper().replace('_', ' ')
        
        # Check if we have a template for this section (try both formats)
        template = self.section_templates.get(template_key_underscore) or self.section_templates.get(template_key_space)
        if not template:
            print(f"No template found for section: {most_appropriate}")
            print(f"Available templates: {list(self.section_templates.keys())}")
            logger.warning(f"No template found for section: {most_appropriate}")
            return None
        
        logger.info(f"Stage 2 (template_fact_extraction): Extracting template-specific facts for {most_appropriate}...")
        
        # Build prompt from summary only (NO markdown document)
        prompt = self._build_template_extraction_prompt_from_summary(
            template=template,
            summary=summary
        )
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-2024-08-06",
                messages=[
                    {"role": "system", "content": f"You are extracting specific facts for {most_appropriate} cases from the provided summary. Return ONLY valid JSON matching the template schema."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.1,
                max_tokens=4000
            )
            
            content = response.choices[0].message.content
            template_facts = json.loads(content)
            
            logger.info(f"Stage 2 (template_fact_extraction) complete: Extracted {most_appropriate}-specific facts")
            
            return {
                'template_id': most_appropriate,
                'template_schema': template,
                'extracted_facts': template_facts
            }
            
        except Exception as e:
            logger.error(f"Template-specific extraction failed: {e}", exc_info=True)
            return None
    
    def _build_template_extraction_prompt_from_summary(
        self,
        template: Dict[str, Any],
        summary: ComprehensiveExtraction
    ) -> str:
        """
        Build prompt for template-specific extraction using ONLY summary data.
        Does NOT include the original markdown document.
        """
        
        # Extract template schema
        template_schema = json.dumps(template.get('json_schema', {}), indent=2)
        
        # Format case facts
        case_facts_text = f"""Prosecution Version: {summary.case_facts.prosecution_version}
Defence Version: {summary.case_facts.defence_version}
Timeline: {', '.join(summary.case_facts.timeline_of_events) if summary.case_facts.timeline_of_events else 'Not available'}
Location: {summary.case_facts.incident_location}
Motive: {summary.case_facts.motive_alleged}"""
        
        # Format evidence
        witness_summary = f"{len(summary.evidence.witness_testimonies)} witnesses recorded" if summary.evidence else "No witnesses"
        evidence_text = f"""Medical Evidence: {summary.evidence.medical_evidence if summary.evidence else ''}
Forensic Evidence: {summary.evidence.forensic_evidence if summary.evidence else ''}
Documentary Evidence: {', '.join(summary.evidence.documentary_evidence) if summary.evidence and summary.evidence.documentary_evidence else 'None'}
Recovery/Seizure: {summary.evidence.recovery_and_seizure if summary.evidence else ''}
Witnesses: {witness_summary}"""
        
        # Use the template_fact_extraction prompt
        prompt = self.template_fact_prompt.replace('{template_schema}', template_schema)
        prompt = prompt.replace('{case_facts}', case_facts_text)
        prompt = prompt.replace('{evidence}', evidence_text)
        
        return prompt
    
    def _create_empty_extraction(self) -> ComprehensiveExtraction:
        """Create empty extraction when parsing fails."""
        return ComprehensiveExtraction(
            metadata=WeaviateMetadata(),
            case_facts=CaseFacts(),
            issues_for_determination=[],
            evidence=Evidence(),
            arguments=Arguments(),
            reasoning=Reasoning(),
            judgement=Judgement()
        )
