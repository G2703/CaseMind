"""
Simplified Fact Extraction Module
Extracts structured facts from legal case text using templates and LLM.
"""
import json
import logging
from typing import Dict, Any, Optional
from openai import OpenAI
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

class FactExtractor:
    """Simplified fact extractor using LLM with structured output."""
    
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
            self.logger.warning("No OpenAI API key provided. LLM extraction will not be available.")
    
    def extract_facts(self, case_text: str, template, extraction_schema: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract facts from case text using template schema.
        
        Args:
            case_text (str): Full case text
            template: Template object/dict containing field definitions
            extraction_schema (Dict): Schema created by TemplateLoader
            
        Returns:
            Dict[str, Any]: Extracted facts organized by tiers
        """
        try:
            # Handle template as either dict or object
            template_id = template.get('node_id') if isinstance(template, dict) else getattr(template, 'node_id', 'unknown')
            template_label = template.get('label') if isinstance(template, dict) else getattr(template, 'label', 'Unknown Template')
            
            self.logger.info(f"Extracting facts using template: {template_id}")

            # Extract facts using LLM - this returns the structured data directly from OpenAI
            facts_dict = self._extract_with_llm(case_text, extraction_schema)
            
            # Add metadata to the extracted facts
            facts_dict['template_id'] = template_id
            facts_dict['template_label'] = template_label
            facts_dict['extraction_confidence'] = 1.0  # Using structured output guarantees completion
            facts_dict['extraction_timestamp'] = datetime.now().isoformat()
            
            return facts_dict
            
        except Exception as e:
            self.logger.error(f"Error extracting facts: {e}")
            raise
    
    def _extract_with_llm(self, case_text: str, extraction_schema: Dict[str, Any]) -> Dict[str, Any]:
        """Extract facts using OpenAI LLM with structured output."""
        
        if self.client is None:
            self.logger.error("OpenAI client not available. Cannot perform LLM extraction.")
            raise RuntimeError("OpenAI client not initialized. Please provide a valid API key.")
        # Create structured prompt
        prompt = self._create_extraction_prompt(case_text, extraction_schema)

        # Extract response format from template
        response_format = {
            "type": extraction_schema.get("type", "json_schema"),
            "json_schema": extraction_schema.get("json_schema", {})
        }
        # print(response_format)

        # Generate response using OpenAI API with template as response format
        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=[
                {"role": "system", "content": "You are an expert legal analyst specializing in Indian court judgments. Extract detailed factual information from legal cases and format as structured JSON. Provide comprehensive, accurate descriptions for each field based on the case text."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.6,
            max_tokens=4096,
            response_format=response_format
        )

        # Parse LLM response
        facts = self._parse_llm_response(response.choices[0].message.content)

        return facts
    
    def _create_extraction_prompt(self, case_text: str, extraction_schema: Dict[str, Any]) -> str:
        """Create structured prompt for LLM-based fact extraction."""
        
        # Truncate text if too long
        if len(case_text) > 15000:
            text_sample = case_text[:15000] + "... [truncated]"
        else:
            text_sample = case_text
        
        # Get template information
        template_label = extraction_schema.get('label', 'Unknown')
        sections = extraction_schema.get('sections', [])
        
        prompt = f"""Extract detailed factual information from this Indian legal case document and organize it according to the structured format.

**CASE CLASSIFICATION**: {template_label}
**LEGAL SECTIONS**: {', '.join(sections) if sections else 'General'}

**EXTRACTION GUIDELINES**:

**TIER 1 - DETERMINATIVE FACTS**: Core facts that determine guilt, liability, or legal outcomes
**TIER 2 - MATERIAL FACTS**: Facts that significantly affect rights, duties, or case outcome  
**TIER 3 - CONTEXTUAL FACTS**: Environmental and circumstantial details
**TIER 4 - PROCEDURAL FACTS**: Court metadata, case details, and procedural information
**RESIDUAL DETAILS**: Any other relevant facts not captured above

**EXTRACTION RULES**:
1. Provide complete descriptive answers using full sentences
2. Extract facts directly from the case text
3. Be comprehensive and accurate
4. If a field is not found in the text, use null
5. Organize facts according to their legal significance

**LEGAL CASE DOCUMENT**:
{text_sample}
"""
        return prompt
    
    def _parse_llm_response(self, llm_response: str) -> Dict[str, Any]:
        """Parse LLM response and extract facts."""
        # Clean the response
        json_text = llm_response.strip()
        
        # Remove markdown formatting if present
        if json_text.startswith('```json'):
            json_text = json_text[7:]
        if json_text.endswith('```'):
            json_text = json_text[:-3]
        
        json_text = json_text.strip()
        
        # Parse JSON
        facts = json.loads(json_text)
        
        return facts
    
    def save_extracted_facts(self, extracted_facts: Dict[str, Any], output_path: str):
        """Save extracted facts to JSON file."""
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(extracted_facts, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"Extracted facts saved to: {output_path}")
            
        except Exception as e:
            self.logger.error(f"Error saving extracted facts: {e}")
            raise

def main():
    """Example usage of simplified fact extractor."""
    extractor = FactExtractor()
    
    # Sample case text
    sample_text = """# Abdul Nasar vs State of Kerla

    """
    
    # Sample template with response format structure
    template = {
        "node_id": "ipc_397",
        "label": "Robbery or dacoity, with attempt to cause death or grievous hurt (IPC 397)",
        "sections": ["IPC 397"],
        "type": "json_schema",
        "json_schema": {
            "name": "fact_extraction",
            "schema": {
                "type": "object",
                "properties": {
                    "tier_1_determinative": {
                        "type": "object",
                        "properties": {
                            "attempt_to_extract_cash": {"type": "string", "description": "Attempt to extract cash or valuables"},
                            "threat_to_kill": {"type": "string", "description": "Threats to kill or cause harm"},
                            "weapon_used": {"type": "string", "description": "Type of weapon used"},
                            "injury_detail": {"type": "string", "description": "Details of injuries caused"}
                        },
                        "required": ["attempt_to_extract_cash", "threat_to_kill", "weapon_used", "injury_detail"],
                        "additionalProperties": False
                    },
                    "tier_2_material": {
                        "type": "object",
                        "properties": {
                            "victim_identity": {"type": "string", "description": "Name or identity of victim"},
                            "number_of_perpetrators": {"type": "string", "description": "Number of people involved"}
                        },
                        "required": ["victim_identity", "number_of_perpetrators"],
                        "additionalProperties": False
                    },
                    "tier_3_contextual": {
                        "type": "object",
                        "properties": {
                            "incident_date_time": {"type": "string", "description": "Date and time of incident"},
                            "incident_location": {"type": "string", "description": "Location where incident occurred"}
                        },
                        "required": ["incident_date_time", "incident_location"],
                        "additionalProperties": False
                    },
                    "tier_4_procedural": {
                        "type": "object",
                        "properties": {
                            "case_number": {"type": "string", "description": "Official case number"},
                            "case_title": {"type": "string", "description": "Full case title"},
                            "court_name": {"type": "string", "description": "Name of the court"},
                            "judgment_date": {"type": "string", "description": "Date of judgment"},
                            "appellant": {"type": "string", "description": "Name of appellant"},
                            "respondent": {"type": "string", "description": "Name of respondent"}
                        },
                        "required": ["case_number", "case_title", "court_name", "judgment_date", "appellant", "respondent"],
                        "additionalProperties": False
                    },
                    "residual_details": {
                        "type": "object",
                        "properties": {
                            "additional_facts": {"type": "string", "description": "Any other relevant facts"}
                        },
                        "required": ["additional_facts"],
                        "additionalProperties": False
                    }
                },
                "required": ["tier_1_determinative", "tier_2_material", "tier_3_contextual", "tier_4_procedural", "residual_details"],
                "additionalProperties": False
            },
            "strict": True
        }
    }
    
    try:
        facts = extractor.extract_facts(sample_text, template, template)
        print("Extracted Facts:")
        print(json.dumps(facts, indent=2))
        
        print(f"\nExtraction completed with confidence: {facts.get('extraction_confidence', 'N/A')}")
        print(f"Template used: {facts.get('template_label', 'N/A')}")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()