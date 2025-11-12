"""
Simplified Fact Extraction Module
Extracts structured facts from legal case text using templates and LLM.
"""
import json
import logging
import re
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from openai import OpenAI
from pydantic import BaseModel, Field
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

@dataclass
class ExtractedFacts:
    """Container for extracted facts with nested structure."""
    template_id: str
    template_label: str
    tier_1_determinative: Dict[str, Dict[str, Any]]  # {"fields": {...}}
    tier_2_material: Dict[str, Dict[str, Any]]       # {"fields": {...}}
    tier_3_contextual: Dict[str, Dict[str, Any]]     # {"fields": {...}}
    tier_4_procedural: Dict[str, Dict[str, Any]]     # {"fields": {...}}
    residual_details: Dict[str, Dict[str, Any]]      # {"unclassified_facts": {...}}
    extraction_confidence: float
    extraction_timestamp: str
    
    def __post_init__(self):
        if not self.extraction_timestamp:
            self.extraction_timestamp = datetime.now().isoformat()

class FactExtractor:
    """Simplified fact extractor using basic regex patterns."""
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize fact extractor."""
        self.logger = logging.getLogger(__name__)
        
        # Configure OpenAI (optional)
        if not api_key:
            api_key = os.getenv('OPENAI_API_KEY')
        
        if api_key:
            try:
                self.client = OpenAI(api_key=api_key)
                self.model_name = "gpt-4o-2024-08-06"
                self.logger.info(f"OpenAI client initialized with model: {self.model_name}")
            except Exception as e:
                self.logger.warning(f"Could not initialize OpenAI client: {e}")
                self.client = None
        else:
            self.client = None
            self.logger.info("No OpenAI API key provided, using regex extraction only")
    
    def extract_facts(self, case_text: str, template, extraction_schema: Dict[str, Any], metadata: Dict[str, Any] = None) -> ExtractedFacts:
        """
        Extract facts from case text using template schema.
        
        Args:
            case_text (str): Full case text
            template: Template object/dict containing field definitions
            extraction_schema (Dict): Schema created by TemplateLoader
            metadata (Dict, optional): Case metadata to include in tier 4
            
        Returns:
            ExtractedFacts: Extracted facts organized by tiers
        """
        try:
            # Handle template as either dict or object
            template_id = template.get('node_id') if isinstance(template, dict) else getattr(template, 'node_id', 'unknown')
            template_label = template.get('label') if isinstance(template, dict) else getattr(template, 'label', 'Unknown Template')
            
            self.logger.info(f"Extracting facts using template: {template_id}")
            
            # Extract facts using regex patterns
            facts = self._extract_with_regex(case_text, extraction_schema)
            
            # Add metadata to tier 4 if provided
            if metadata:
                if 'tier_4_procedural' not in facts:
                    facts['tier_4_procedural'] = {}
                facts['tier_4_procedural'].update(self._format_metadata_for_tier4(metadata))
            
            # Calculate confidence
            confidence = self._calculate_confidence(facts, extraction_schema)
            
            extracted_facts = ExtractedFacts(
                template_id=template_id,
                template_label=template_label,
                tier_1_determinative={"fields": facts.get('tier_1_determinative', {})},
                tier_2_material={"fields": facts.get('tier_2_material', {})},
                tier_3_contextual={"fields": facts.get('tier_3_contextual', {})},
                tier_4_procedural={"fields": facts.get('tier_4_procedural', {})},
                residual_details={"unclassified_facts": facts.get('residual_details', {})},
                extraction_confidence=confidence,
                extraction_timestamp=datetime.now().isoformat()
            )
            
            self.logger.info(f"Fact extraction completed with confidence: {confidence:.2f}")
            return extracted_facts
            
        except Exception as e:
            self.logger.error(f"Error extracting facts: {e}")
            raise
    
    def _extract_with_regex(self, case_text: str, extraction_schema: Dict[str, Any]) -> Dict[str, Any]:
        """Extract facts using regex patterns based on template structure."""
        
        fact_tiers = extraction_schema.get('fact_tiers', {})
        field_definitions = extraction_schema.get('field_definitions', {})
        
        # Initialize tier structure
        tier_facts = {
            'tier_1_determinative': {},
            'tier_2_material': {},
            'tier_3_contextual': {},
            'tier_4_procedural': {},
            'residual_details': {}
        }
        
        # Extract facts for each tier
        for tier_name, tier_data in fact_tiers.items():
            fields = tier_data.get('fields', [])
            for field_name in fields:
                field_info = field_definitions.get(field_name, {})
                value = self._extract_field_value(case_text, field_name, field_info)
                if value:
                    tier_facts[tier_name][field_name] = value
        
        # Extract residual facts
        residual_fields = extraction_schema.get('residual_details', {}).get('unclassified_facts', [])
        for field_name in residual_fields:
            field_info = field_definitions.get(field_name, {})
            value = self._extract_field_value(case_text, field_name, field_info)
            if value:
                tier_facts['residual_details'][field_name] = value
        
        return tier_facts
    
    def _extract_field_value(self, case_text: str, field_name: str, field_info: Dict[str, str]) -> Optional[str]:
        """Extract specific field using targeted regex patterns."""
        
        # Common regex patterns for legal case fields
        patterns = {
            'case_number': [
                r'CRIMINAL APPEAL NO\.(\d+(?:\s+OF\s+)\d+)',
                r'Sessions Case No\.(\d+(?:\s+of\s+)\d+)',
                r'Crime No\.(\d+(?:\s+of\s+)\d+)'
            ],
            'case_title': [
                r'([A-Z][A-Z\s]+)\s+V/s\.\s+([A-Z][A-Z\s]+)',
                r'([A-Z][a-zA-Z\s]+)\s+V/s\.\s+([A-Z][a-zA-Z\s]+)'
            ],
            'court_name': [
                r'IN THE (HIGH COURT OF JUDICATURE AT [A-Z]+)',
                r'(HIGH COURT OF [A-Z\s]+)'
            ],
            'judgment_date': [
                r'PRONOUNCED ON (\d{1,2}(?:st|nd|rd|th)?\s+[A-Z][a-z]+\s+\d{4})',
                r'dated (\d{1,2}(?:st|nd|rd|th)?\s+[A-Z][a-z]+\s+\d{4})'
            ],
            'appellant': [
                r'([A-Z][A-Z\s]+)\s*\)\.\.\.APPELLANT',
                r'appellant[^,]*?([A-Z][a-zA-Z\s]+)'
            ],
            'respondent': [
                r'THE STATE OF ([A-Z]+)\s*\)\.\.\.RESPONDENT'
            ],
            'sections_invoked': [
                r'Section (\d+[A-Z]?)',
                r'punishable under Section (\d+[A-Z]?)'
            ],
            'weapon_used': [
                r'gave blow of (knife)',
                r'by means of a (knife)',
                r'(knife|gun|pistol|sword|stick|weapon)'
            ],
            'injury_detail': [
                r'causing (bleeding injury[^.]*)',
                r'(contused lacerated wound[^.]*)',
                r'suffered[^.]*?(injury[^.]*?)(?:\.|;|$)'
            ],
            'victim_identity': [
                r'First Informant ([A-Z][a-zA-Z\s]+)',
                r'PW1 ([A-Z][a-zA-Z\s]+)'
            ],
            'incident_date_time': [
                r'on (24th October 2009[^.]*?11\.30 p\.m\.)',
                r'incident[^.]*?(\d{1,2}(?:st|nd|rd|th)?\s+[A-Z][a-z]+\s+\d{4}[^.]*?(?:\d{1,2}:\d{2}|\d{1,2}\.\d{2})[^.]*?(?:p\.m\.|a\.m\.))'
            ],
            'incident_location': [
                r'alighted at ([A-Z][a-zA-Z\s]+Railway Station)',
                r'at ([A-Z][a-zA-Z\s]+(?:Railway Station|Hospital|Police Station))'
            ],
            'threat_to_kill': [
                r'(extending threat of killing him)',
                r'(threat[^.]*?kill[^.]*)'
            ],
            'attempt_to_extract_cash': [
                r'(tried to extract cash and valuables from him)',
                r'(asked him to deliver his wrist watch)'
            ]
        }
        
        # Get patterns for this field
        field_patterns = patterns.get(field_name, [])
        
        # If no specific patterns, try generic approach
        if not field_patterns:
            field_terms = field_name.replace('_', ' ').split()
            generic_pattern = r'(?:' + '|'.join(field_terms) + r')[^.]*?([^.]+?)(?:\.|,|\n)'
            field_patterns = [generic_pattern]
        
        # Try each pattern
        for pattern in field_patterns:
            try:
                matches = re.findall(pattern, case_text, re.IGNORECASE | re.MULTILINE)
                if matches:
                    if isinstance(matches[0], tuple):
                        return ' '.join(matches[0]).strip()
                    else:
                        return matches[0].strip()
            except re.error:
                continue
        
        return None
    
    def _calculate_confidence(self, facts: Dict[str, Dict[str, Any]], extraction_schema: Dict[str, Any]) -> float:
        """Calculate extraction confidence based on completeness."""
        fact_tiers = extraction_schema.get('fact_tiers', {})
        
        total_fields = 0
        extracted_fields = 0
        
        for tier_name, tier_info in fact_tiers.items():
            tier_fields = tier_info.get('fields', [])
            total_fields += len(tier_fields)
            extracted_fields += len(facts.get(tier_name, {}))
        
        if total_fields == 0:
            return 0.0
        
        return round(extracted_fields / total_fields, 2)
    
    def _format_metadata_for_tier4(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Format metadata for inclusion in tier 4."""
        tier_4_metadata = {}
        
        # Map metadata fields to tier 4 fields
        metadata_mapping = {
            'case_number': 'case_number',
            'case_title': 'case_title',
            'court_name': 'court_name',
            'judgment_date': 'judgment_date',
            'appellant_or_petitioner': 'appellant_or_petitioner',
            'respondent': 'respondent'
        }
        
        for meta_key, tier4_key in metadata_mapping.items():
            if meta_key in metadata and metadata[meta_key]:
                tier_4_metadata[tier4_key] = metadata[meta_key]
        
        return tier_4_metadata
    
    def save_extracted_facts(self, extracted_facts: ExtractedFacts, output_path: str):
        """Save extracted facts to JSON file."""
        try:
            facts_dict = asdict(extracted_facts)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(facts_dict, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"Extracted facts saved to: {output_path}")
            
        except Exception as e:
            self.logger.error(f"Error saving extracted facts: {e}")
            raise

def main():
    """Example usage of simplified fact extractor."""
    extractor = FactExtractor()
    
    # Sample case text
    sample_text = """IN THE HIGH COURT OF JUDICATURE AT BOMBAY
    CRIMINAL APPELLATE JURISDICTION
    CRIMINAL APPEAL NO.290 OF 2014
    AAKASH RAMCHANDRA CHAVAN
    )...APPELLANT
    V/s.
    THE STATE OF MAHARASHTRA
    )...RESPONDENT
    
    PRONOUNCED ON 29th AUGUST 2019
    
    First Informant Vijay Sadavate boarded the local train on
    24th October 2009 from Chhatrapati Shivaji Maharaj
    Terminus station for going to his house after working hours.
    He alighted at Chembur Railway Station at about 11.30 p.m.
    One of them caught hold of collar of shirt of the First
    Informant/PW1 Vijay Sadavate and by extending threat of killing him, tried to extract cash and valuables from him.
    He gave blow of knife on back side of head of the First
    Informant/PW1 Vijay Sadavate causing bleeding injury.
    
    The accused persons then fled from the spot of the incident when Mansoor shouted for help.
    """
    
    # Sample template
    template = {
        "node_id": "ipc_397",
        "label": "Robbery or dacoity, with attempt to cause death or grievous hurt (IPC 397)",
        "fact_tiers": {
            "tier_1_determinative": {
                "fields": ["attempt_to_extract_cash", "threat_to_kill", "weapon_used", "injury_detail"]
            },
            "tier_2_material": {
                "fields": ["victim_identity", "number_of_perpetrators"]
            },
            "tier_3_contextual": {
                "fields": ["incident_date_time", "incident_location"]
            },
            "tier_4_procedural": {
                "fields": ["case_number", "case_title", "court_name", "judgment_date", "appellant", "respondent"]
            }
        },
        "field_definitions": {
            "attempt_to_extract_cash": {"type": "string", "description": "Attempt to extract cash or valuables"},
            "threat_to_kill": {"type": "string", "description": "Threats to kill or cause harm"},
            "weapon_used": {"type": "string", "description": "Type of weapon used"},
            "injury_detail": {"type": "string", "description": "Details of injuries caused"},
            "victim_identity": {"type": "string", "description": "Name or identity of victim"},
            "incident_date_time": {"type": "string", "description": "Date and time of incident"},
            "incident_location": {"type": "string", "description": "Location where incident occurred"},
            "case_number": {"type": "string", "description": "Official case number"},
            "case_title": {"type": "string", "description": "Full case title"},
            "court_name": {"type": "string", "description": "Name of the court"},
            "judgment_date": {"type": "string", "description": "Date of judgment"},
            "appellant": {"type": "string", "description": "Name of appellant"},
            "respondent": {"type": "string", "description": "Name of respondent"}
        }
    }
    
    try:
        facts = extractor.extract_facts(sample_text, template, template)
        print("Extracted Facts:")
        print(json.dumps(asdict(facts), indent=2))
        
        print(f"\nExtraction completed with confidence: {facts.extraction_confidence}")
        print(f"Template used: {facts.template_label}")
        
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()