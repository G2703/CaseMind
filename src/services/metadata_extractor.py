"""
Metadata extraction service using OpenAI LLM.
Implements IMetadataExtractor interface.
"""

import logging
import json
from typing import Dict, Any, Optional, List
from pathlib import Path
import openai
from pydantic import BaseModel, Field, ValidationError

from core.interfaces import IMetadataExtractor
from core.models import CaseMetadata
from core.exceptions import MetadataExtractionError
from core.config import Config

logger = logging.getLogger(__name__)


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

    class Config:
        extra = 'ignore'


class MetadataExtractor(IMetadataExtractor):
    """
    Extract metadata from case text using OpenAI LLM.
    Uses GPT-4 for structured extraction of case metadata.
    """

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the metadata extractor and OpenAI client.
        """
        self.app_config = Config()
        self.api_key = api_key or getattr(self.app_config, 'openai_api_key', None)
        if not self.api_key:
            raise MetadataExtractionError("OpenAI API key not configured")

        openai.api_key = self.api_key
        self.client = openai.OpenAI(api_key=self.api_key)
        self.model_name = "gpt-4o-2024-08-06"
        logger.info("Metadata extractor initialized with structured output support")

    async def extract(self, text: str, file_path: Optional[Path] = None) -> Dict[str, Any]:
        """
        Extract metadata from case text using structured output API.

        Returns a dict with validated fields; fills sensible defaults when needed.
        """
        try:
            # Truncate text if too long (reduce to 4000 chars to leave room for comprehensive prompt)
            # The prompt itself is ~2000 tokens, so 4000 chars (~1000 tokens) + prompt + response fits in 8192 limit
            if len(text) > 8000:
                text_sample = text[:8000] + "... [truncated]"
                logger.warning(f"Text truncated from {len(text)} to 8000 characters")
            else:
                text_sample = text

            # Build comprehensive prompt for Indian legal cases
            prompt_content = self._create_structured_metadata_prompt(text_sample)

            logger.info("Calling OpenAI API for metadata extraction using structured output...")
            
            # Generate response using structured output API
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
                temperature=0.5,
                max_tokens=1024  # Reduced from 1024 to leave more room for input
            )

            # Get structured metadata directly from parsed response
            structured_metadata = response.choices[0].message.parsed

            if structured_metadata:
                # Convert Pydantic model to dict (compatible with Pydantic v1 and v2)
                try:
                    metadata_dict = structured_metadata.model_dump()  # Pydantic v2
                except AttributeError:
                    metadata_dict = structured_metadata.dict()  # Pydantic v1
                
                # Ensure sections_invoked is a list (not None)
                if metadata_dict.get('sections_invoked') is None:
                    metadata_dict['sections_invoked'] = []
                
                # Fill missing required fields with defaults
                for fld in ['case_title', 'court_name', 'judgment_date', 'most_appropriate_section']:
                    if not metadata_dict.get(fld):
                        metadata_dict[fld] = 'Unknown'

                # Filename fallback for title
                if file_path and metadata_dict.get('case_title') == 'Unknown':
                    metadata_dict['case_title'] = self._infer_title_from_filename(file_path)

                logger.info(f"Metadata extracted: {metadata_dict.get('case_title', 'Unknown')}")
                return metadata_dict
            else:
                logger.warning("No structured metadata returned")
                return self._get_default_metadata()

        except openai.RateLimitError as e:
            error_msg = (
                "\n" + "="*50 + "\n"
                "⚠️  OPENAI API QUOTA EXCEEDED\n"
            )
            logger.error(error_msg)
            raise MetadataExtractionError(f"OpenAI quota exceeded. Please check your API account and billing. Details: {e}")
        except openai.OpenAIError as e:
            logger.exception(f"OpenAI API error during metadata extraction: {e}")
            raise MetadataExtractionError(f"OpenAI API error: {e}")
        except Exception as e:
            logger.exception(f"Failed to extract metadata. Error: {e}")
            raise MetadataExtractionError(f"Metadata extraction failed: {e}")

    def _create_structured_metadata_prompt(self, text_sample: str) -> str:
        """
        Create a comprehensive prompt for Indian legal case metadata extraction.
        
        Args:
            text_sample: Case document text (pre-truncated if needed)
            
        Returns:
            str: Formatted prompt for structured extraction
        """
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

    def _get_default_metadata(self) -> Dict[str, Any]:
        """
        Return default metadata when extraction fails.
        """
        return {
            'case_number': None,
            'case_title': 'Unknown',
            'court_name': 'Unknown',
            'judgment_date': 'Unknown',
            'appellant_or_petitioner': None,
            'respondent': None,
            'judges_coram': None,
            'counsel_for_appellant': None,
            'counsel_for_respondent': None,
            'sections_invoked': [],
            'most_appropriate_section': 'Unknown',
            'case_type': None,
            'citation': None,
            'acts_and_sections': None
        }

    def _infer_title_from_filename(self, file_path: Path) -> str:
        """
        Infer case title from filename as fallback.
        """
        filename = file_path.stem
        title = filename.replace('_', ' ').replace('Vs.', 'vs').replace('vs', 'Vs.')
        return title if title and title != 'Unknown' else 'Unknown Case'
