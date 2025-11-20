"""
Metadata Extraction Module for Legal Cases
Extracts key metadata from legal case documents using LLM with structured output.
"""
import json
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from openai import OpenAI
from pydantic import BaseModel, Field
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# Pydantic model for structured metadata extraction
class StructuredCaseMetadata(BaseModel):
    """Pydantic model for structured case metadata extraction."""
    
    case_number: Optional[str] = Field(None, description="Case number (e.g., 'Crl. Appeal No.1192/2011')")
    case_title: Optional[str] = Field(None, description="Full case title (e.g., 'Afsar & Anr. vs. State of Delhi')")
    court_name: Optional[str] = Field(None, description="Name of the court (e.g., 'High Court of Delhi')")
    judgment_date: Optional[str] = Field(None, description="Date of judgment (e.g., '15th March, 2012')")
    appellant_or_petitioner: Optional[str] = Field(None, description="Name of appellant/petitioner")
    respondent: Optional[str] = Field(None, description="Name of respondent")
    judges_coram: Optional[str] = Field(None, description="Names of judges")
    counsel_for_appellant: Optional[str] = Field(None, description="Counsel for appellant/petitioner")
    counsel_for_respondent: Optional[str] = Field(None, description="Counsel for respondent")
    sections_invoked: Optional[List[str]] = Field(None, description="All legal sections mentioned (e.g., ['IPC 376', 'IPC 363', 'POCSO 6'])")
    most_appropriate_section: Optional[str] = Field(None, description="The PRIMARY legal section that best represents this case based on severity and centrality to the facts (e.g., 'IPC 376' for rape case, 'IPC 302' for murder case). Choose the most serious offense if multiple sections are present.")
    case_type: Optional[str] = Field(None, description="Type of case (e.g., 'Criminal Appeal', 'Writ Petition')")
    citation: Optional[str] = Field(None, description="Case citation if available")
    acts_and_sections: Optional[str] = Field(None, description="Comma-separated list of relevant Acts and Sections")

@dataclass
class CaseMetadata:
    """Data class for case metadata."""
    case_number: Optional[str] = None
    case_title: Optional[str] = None
    court_name: Optional[str] = None
    judgment_date: Optional[str] = None
    appellant_or_petitioner: Optional[str] = None
    respondent: Optional[str] = None
    judges_coram: Optional[str] = None
    counsel_for_appellant: Optional[str] = None
    counsel_for_respondent: Optional[str] = None
    sections_invoked: List[str] = None
    most_appropriate_section: Optional[str] = None
    case_type: Optional[str] = None
    citation: Optional[str] = None
    acts_and_sections: Optional[str] = None
    
    def __post_init__(self):
        if self.sections_invoked is None:
            self.sections_invoked = []

class MetadataExtractor:
    """Extracts metadata from legal case documents using LLM."""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize metadata extractor.
        
        Args:
            api_key (str, optional): OpenAI API key. If None, will use environment variable.
        """
        self.logger = logging.getLogger(__name__)
        
        # Configure OpenAI
        if not api_key:
            api_key = os.getenv('OPENAI_API_KEY')
            if not api_key:
                raise ValueError("OpenAI API key not provided")
        
        try:
            self.client = OpenAI(api_key=api_key)
            self.model_name = "gpt-4o-2024-08-06"
            self.logger.info(f"Successfully initialized OpenAI client for metadata extraction")
        except Exception as e:
            self.logger.warning(f"Could not initialize OpenAI client: {e}")
            self.client = None
    
    def extract_metadata(self, case_text: str) -> CaseMetadata:
        """
        Extract metadata from case document text using structured output.
        
        Args:
            case_text (str): Full text of the legal case document
            
        Returns:
            CaseMetadata: Extracted metadata
        """
        try:
            self.logger.info("Extracting metadata using structured output")
            
            if not self.client:
                raise Exception("OpenAI client not available")
            
            # Create prompt for structured metadata extraction
            prompt_content = self._create_structured_metadata_prompt(case_text)
            
            # Generate response using structured output
            response = self.client.beta.chat.completions.parse(
                model=self.model_name,
                messages=[
                    {
                        "role": "system", 
                        "content": "You are a legal metadata extraction specialist. Extract comprehensive case metadata from Indian legal documents with high accuracy."
                    },
                    {
                        "role": "user", 
                        "content": prompt_content
                    }
                ],
                response_format=StructuredCaseMetadata,
                temperature=0.1,
                max_tokens=1024
            )
            
            # Get structured metadata
            structured_metadata = response.choices[0].message.parsed
            
            if structured_metadata:
                # Convert to CaseMetadata dataclass
                metadata_dict = structured_metadata.model_dump()
                metadata = CaseMetadata(**metadata_dict)
                self.logger.info("Metadata extraction completed successfully")
                return metadata
            else:
                self.logger.warning("No structured metadata returned")
                return CaseMetadata()
            
        except Exception as e:
            self.logger.error(f"Error extracting metadata: {e}")
            return CaseMetadata()
    
    def _create_structured_metadata_prompt(self, case_text: str) -> str:
        """
        Create a structured prompt for metadata extraction.
        
        Args:
            case_text (str): Case document text
            
        Returns:
            str: Formatted prompt for structured extraction
        """
        # Truncate text if too long (keep first 8000 chars for context)
        if len(case_text) > 8000:
            text_sample = case_text[:8000] + "... [truncated]"
        else:
            text_sample = case_text
        
        prompt = f"""
Analyze the following Indian legal case document and extract comprehensive metadata with special focus on identifying the most appropriate legal section.

Legal Document Text:
---
{text_sample}
---

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
- Format as "IPC 376", "POCSO 6", "CrPC 482", etc.

For most_appropriate_section (MOST IMPORTANT):
- Analyze the entire case to identify which section represents the PRIMARY offense
- Consider these factors in order of priority:
  1. SEVERITY: More serious offenses take precedence (murder > theft, rape > harassment)
  2. CENTRALITY: The section most discussed in the judgment and central to the case outcome
  3. CONVICTION: If convicted, the section under which conviction was secured
  4. CHARGES: The main charge that the case revolves around

SEVERITY HIERARCHY (select higher severity if multiple sections):
- Capital offenses: IPC 302 (murder), IPC 396 (dacoity with murder)
- Sexual offenses: IPC 376 (rape), POCSO 4/6 (sexual assault), IPC 354 (molestation)  
- Violence: IPC 307 (attempt murder), IPC 304 (culpable homicide), IPC 326 (grievous hurt)
- Robbery/Dacoity: IPC 397 (dacoity with attempt to cause death), IPC 395 (dacoity), IPC 394 (robbery with hurt), IPC 392 (robbery)
- Kidnapping: IPC 363 (kidnapping), IPC 364 (kidnapping to murder)
- Property crimes: IPC 379 (theft), IPC 420 (cheating), IPC 384 (extortion)
- Simple offenses: IPC 323 (hurt), IPC 341 (wrongful restraint)

SPECIFIC GUIDANCE FOR DACOITY CASES:
- If case mentions "dacoity", "five or more persons", "group robbery", or "gang crime", look for IPC 395/397
- IPC 395: Basic dacoity (5+ persons committing robbery)
- IPC 397: Dacoity with attempt to cause death or grievous hurt (higher severity)
- If both IPC 395 and IPC 397 are present, choose IPC 397 as most_appropriate_section
- If dacoity with murder (IPC 302), choose IPC 302 as most severe

DECISION LOGIC:
1. If case involves multiple sections, choose the one with highest legal severity
2. If same severity level, choose the section most central to the case facts
3. If still unclear, choose the section with most evidence/discussion in judgment
4. Prefer specific sections over general ones (IPC 376 over IPC 375)

Examples:
- Case with IPC 376, IPC 363, IPC 506 → most_appropriate_section: "IPC 376" (rape is most severe)
- Case with IPC 394, IPC 397, IPC 323 → most_appropriate_section: "IPC 397" (highest severity in robbery category)
- Case with IPC 395, IPC 34, IPC 323 → most_appropriate_section: "IPC 395" (dacoity is most severe)
- Case with IPC 397, IPC 395, IPC 302 → most_appropriate_section: "IPC 302" (murder trumps dacoity)
- Case with only IPC 323, IPC 341 → most_appropriate_section: "IPC 323" (hurt more serious than restraint)
- Dacoity case with multiple sections → Look for IPC 395 (dacoity) or IPC 397 (dacoity with death attempt)

Other instructions:
- Be precise and extract exact text as it appears
- Use null for fields that cannot be clearly identified
- If multiple judges, include all names
        """
        return prompt
    
    def _infer_section_from_text(self, case_text: str) -> Optional[str]:
        """
        Infer the most appropriate section from case text using pattern matching.
        This is a fallback when LLM extraction fails.
        
        Args:
            case_text (str): Case document text
            
        Returns:
            Optional[str]: Inferred section or None
        """
        text_lower = case_text.lower()
        
        # Dacoity patterns
        dacoity_patterns = [
            'dacoity', 'five or more persons', 'group robbery', 'gang crime',
            'section 395', 'ipc 395', '395', 'section 397', 'ipc 397', '397'
        ]
        
        # Murder patterns  
        murder_patterns = [
            'murder', 'section 302', 'ipc 302', '302', 'causing death'
        ]
        
        # Rape patterns
        rape_patterns = [
            'rape', 'section 376', 'ipc 376', '376', 'sexual assault', 'pocso'
        ]
        
        # Robbery patterns
        robbery_patterns = [
            'robbery', 'section 392', 'ipc 392', '392', 'section 394', 'ipc 394', '394'
        ]
        
        # Check patterns in order of severity
        if any(pattern in text_lower for pattern in murder_patterns):
            return "IPC 302"
        elif any(pattern in text_lower for pattern in rape_patterns):
            return "IPC 376"
        elif 'section 397' in text_lower or 'ipc 397' in text_lower or '397' in text_lower:
            return "IPC 397"  # Dacoity with death attempt (higher severity)
        elif any(pattern in text_lower for pattern in dacoity_patterns):
            return "IPC 395"  # Basic dacoity
        elif any(pattern in text_lower for pattern in robbery_patterns):
            return "IPC 392"
        
        return None
    
    def _infer_section_from_path(self, file_path: str) -> Optional[str]:
        """
        Infer the most appropriate section from file path.
        This is a fallback when both LLM extraction and text analysis fail.
        
        Args:
            file_path (str): Path to the case file
            
        Returns:
            Optional[str]: Inferred section or None
        """
        path_lower = file_path.lower()
        
        # Check directory structure for case type hints
        if 'dacoity' in path_lower:
            return "IPC 395"  # Default to basic dacoity
        elif 'rape' in path_lower:
            return "IPC 376"
        elif 'murder' in path_lower:
            return "IPC 302"
        elif 'robbery' in path_lower:
            return "IPC 392"
        elif 'theft' in path_lower:
            return "IPC 379"
        elif 'kidnapping' in path_lower:
            return "IPC 363"
        
        return None
    
    def _create_metadata_prompt(self, case_text: str) -> str:
        """
        Create a structured prompt for metadata extraction.
        
        Args:
            case_text (str): Case document text
            
        Returns:
            str: Formatted prompt
        """
        # Truncate text if too long (keep first 8000 chars for context)
        if len(case_text) > 8000:
            text_sample = case_text[:8000] + "... [truncated]"
        else:
            text_sample = case_text
        
        prompt = f"""
You are a legal expert tasked with extracting metadata from an Indian legal case document. 
Please analyze the following legal document and extract the metadata in JSON format.

Legal Document Text:
---
{text_sample}
---

Please extract the following metadata and return ONLY a valid JSON object with these fields:

{{
    "case_number": "Case number (e.g., 'Crl. Appeal No.1192/2011')",
    "case_title": "Full case title (e.g., 'Afsar & Anr. vs. State of Delhi')",
    "court_name": "Name of the court (e.g., 'High Court of Delhi')",
    "judgment_date": "Date of judgment (e.g., '15th March, 2012')",
    "appellant_or_petitioner": "Name of appellant/petitioner",
    "respondent": "Name of respondent",
    "judges_coram": "Names of judges",
    "counsel_for_appellant": "Counsel for appellant/petitioner",
    "counsel_for_respondent": "Counsel for respondent",
    "sections_invoked": ["IPC 376", "IPC 363", "POCSO 6"],
    "most_appropriate_section": "The most appropriate legal section applicable to the case",
    "case_type": "Type of case (e.g., 'Criminal Appeal', 'Writ Petition')",
    "citation": "Case citation if available",
    "acts_and_sections": "Comma-separated list of relevant Acts and Sections"
}}

Instructions:
1. Return ONLY the JSON object, no other text
2. Use null for fields that cannot be found
3. For sections_invoked, extract all IPC sections, POCSO sections, and other legal provisions mentioned
4. Be precise and extract exact text as it appears in the document
5. If multiple judges, separate with commas
6. If information is not clearly available, use null rather than guessing

JSON Response:
"""
        return prompt
    
    def extract_metadata_and_facts(self, case_text: str, file_path: str = "") -> Dict[str, Any]:
        """
        Complete pipeline: Extract metadata, load appropriate template, and extract facts.
        
        Args:
            case_text (str): Full text of the legal case document
            
        Returns:
            Dict[str, Any]: Complete extracted case data
        """
        from load_template import TemplateLoader
        from extract_facts import FactExtractor
        from ontology_matcher import OntologyMatcher
        
        try:
            # Step 1: Extract metadata using structured output
            self.logger.info("Step 1: Extracting metadata")
            metadata = self.extract_metadata(case_text)
            
            # print(metadata)

            if not metadata.most_appropriate_section:
                self.logger.warning("No most appropriate section found in metadata")
                # Try to infer from case text or file path
                inferred_section = self._infer_section_from_text(case_text)
                if not inferred_section and file_path:
                    inferred_section = self._infer_section_from_path(file_path)
                    
                if inferred_section:
                    self.logger.info(f"Inferred section from analysis: {inferred_section}")
                    metadata.most_appropriate_section = inferred_section
                    metadata.sections_invoked = [inferred_section] if not metadata.sections_invoked else metadata.sections_invoked
                else:
                    return {
                        'metadata': asdict(metadata),
                        'template_used': None,
                        'extracted_facts': None,
                        'error': 'No appropriate section identified'
                    }
            
            # Step 2: Load template based on most appropriate section
            self.logger.info(f"Step 2: Loading template for section: {metadata.most_appropriate_section}")
            
            # Initialize components
            template_loader = TemplateLoader("templates")
            ontology_matcher = OntologyMatcher("Ontology_schema/ontology_schema.json")
            
            # Find matching template based on the most appropriate section
            metadata_dict = asdict(metadata)
            
            # Override sections_invoked with the most appropriate section for better matching
            metadata_dict['sections_invoked'] = [metadata.most_appropriate_section]
            
            # Match with ontology
            ontology_matches = ontology_matcher.find_matching_nodes(metadata_dict, case_text)
            
            if not ontology_matches:
                self.logger.warning("No ontology matches found")
                return {
                    'metadata': metadata_dict,
                    'template_used': None,
                    'extracted_facts': None,
                    'error': 'No matching template found'
                }
            
            # Get best match
            leaf_matches = ontology_matcher.get_leaf_nodes_only(ontology_matches)
            best_match = ontology_matcher.get_best_match(leaf_matches or ontology_matches)
            
            if not best_match:
                self.logger.warning("No best match found")
                return {
                    'metadata': metadata_dict,
                    'template_used': None,
                    'extracted_facts': None,
                    'error': 'No best template match found'
                }
            
            # Step 3: Load the template
            template = template_loader.load_template(best_match.node_id)
            
            if not template:
                self.logger.warning(f"Template not found for node: {best_match.node_id}")
                return {
                    'metadata': metadata_dict,
                    'template_used': best_match.node_id,
                    'extracted_facts': None,
                    'error': f'Template file not found: {best_match.node_id}'
                }
            
            # Handle template as either dict or object
            template_label = template.get('label') if isinstance(template, dict) else getattr(template, 'label', 'Unknown Template')
            
            # Step 4: Create dynamic extraction schema
            self.logger.info(f"Step 3: Creating extraction schema for template: {template_label}")
            extraction_schema = template_loader.create_extraction_schema(template)
            
            # Step 5: Extract facts using the template
            self.logger.info("Step 4: Extracting facts using structured output")
            fact_extractor = FactExtractor()
            extracted_facts = fact_extractor.extract_facts(
                case_text=case_text,
                template=template,
                extraction_schema=extraction_schema
            )
            
            # Return complete result
            result = {
                'metadata': metadata_dict,
                'template_used': best_match.node_id,
                'template_label': template_label,
                'extracted_facts': extracted_facts,  # Now it's already a dict
                'confidence_score': best_match.confidence_score,
                'extraction_confidence': extracted_facts.get('extraction_confidence', 1.0)
            }
            
            self.logger.info("Complete extraction pipeline completed successfully")
            return result
            
        except Exception as e:
            self.logger.error(f"Error in complete extraction pipeline: {e}")
            return {
                'metadata': asdict(metadata) if 'metadata' in locals() else None,
                'template_used': None,
                'extracted_facts': None,
                'error': str(e)
            }
    
    def save_metadata(self, metadata: CaseMetadata, output_path: str) -> None:
        """
        Save extracted metadata to JSON file.
        
        Args:
            metadata (CaseMetadata): Metadata to save
            output_path (str): Path to save JSON file
        """
        try:
            metadata_dict = asdict(metadata)
            
            # Add extraction timestamp
            metadata_dict['extraction_timestamp'] = datetime.now().isoformat()
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(metadata_dict, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"Metadata saved to {output_path}")
            
        except Exception as e:
            self.logger.error(f"Error saving metadata: {e}")
            raise

def main():
    """Example usage of metadata extractor."""
    extractor = MetadataExtractor()
    
    # Example with sample text
    sample_text = """
    CRIMINAL APPEAL NO. 1192 OF 2011
    HIGH COURT OF DELHI
    
    AFSAR & ANR. VS. STATE OF DELHI
    
    CORAM: HON'BLE MR. JUSTICE S.P. GARG
    
    Sections: IPC 376, IPC 363, POCSO 6
    
    Judgment dated: 15th March, 2012
    """
    
    metadata = extractor.extract_metadata(sample_text)
    print("Extracted Metadata:")
    print(json.dumps(asdict(metadata), indent=2))

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()