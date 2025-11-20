"""
Fact extraction service using OpenAI LLM with template-based prompts.
Implements IFactExtractor interface.
"""

import logging
import json
from typing import Dict, Any
import openai

from core.interfaces import IFactExtractor
from core.models import Template, ExtractedFacts
from core.exceptions import FactExtractionError
from core.config import Config

logger = logging.getLogger(__name__)


class FactExtractor(IFactExtractor):
    """
    Extract structured facts from legal case text using LLM.
    Uses template schema to guide extraction.
    """
    
    FACT_EXTRACTION_PROMPT_TEMPLATE = """You are a legal document analyzer. Extract structured facts from the given legal case text according to the provided template schema.

Template: {template_label}
Template Schema:
{schema}

Guidelines:
- Extract facts according to the 4-tier structure
- Tier 1: Parties involved (appellant, respondent, victim, etc.)
- Tier 2: Incident details (date, time, location, description, etc.)
- Tier 3: Legal aspects (charges, evidence, defenses, etc.)
- Tier 4: Procedural information (FIR, courts, judgments, etc.)
- Return ONLY valid JSON matching the schema
- Use null for missing information
- Be precise and factual

Legal Case Text:
{text}

Return the extracted facts as a JSON object with tiers tier_1_parties, tier_2_incident, tier_3_legal, tier_4_procedural.
"""
    
    def __init__(self, api_key: str = None):
        """
        Initialize fact extractor.
        
        Args:
            api_key: OpenAI API key (uses config if not provided)
        """
        self.config = Config()
        self.api_key = api_key or self.config.openai_api_key
        
        if not self.api_key:
            raise FactExtractionError("OpenAI API key not configured")
        
        openai.api_key = self.api_key
        self.client = openai.OpenAI(api_key=self.api_key)
        logger.info("Fact extractor initialized")
    
    async def extract(self, text: str, template: Template) -> Dict[str, Any]:
        """
        Extract structured facts based on template.
        
        Args:
            text: Legal case text
            template: Template defining extraction schema
            
        Returns:
            Dictionary containing extracted facts
            
        Raises:
            FactExtractionError: If extraction fails
        """
        try:
            # Truncate text if too long to fit within 8192 token limit
            # gpt-4 has 8192 token context limit
            # Allocate: ~1000 tokens for prompt + ~1500 tokens for input text + 1500 tokens for output = ~4000 total
            max_chars = 6000
            if len(text) > max_chars:
                logger.warning(f"Text truncated from {len(text)} to {max_chars} characters")
                text = text[:max_chars] + "\n... [truncated]"
            
            # Build extraction prompt
            prompt = self._build_prompt(text, template)
            
            # Call OpenAI API
            logger.info(f"Calling OpenAI API for fact extraction (template: {template.template_id})...")
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are a legal document fact extractor. Always return valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=1500
            )
            
            # Parse response
            response_text = response.choices[0].message.content.strip()
            facts = self._parse_response(response_text)
            
            logger.info("Facts extracted successfully")
            return facts
            
        except openai.RateLimitError as e:
            error_msg = (
                "\n" + "="*50 + "\n"
                "⚠️  OPENAI API QUOTA EXCEEDED\n"
            )
            logger.error(error_msg)
            raise FactExtractionError(f"OpenAI quota exceeded. Please check your API account. Details: {e}")
        except openai.OpenAIError as e:
            logger.exception(f"OpenAI API error during fact extraction: {e}")
            raise FactExtractionError(f"OpenAI API error: {e}")
        except Exception as e:
            logger.error(f"Failed to extract facts: {e}")
            raise FactExtractionError(f"Fact extraction failed: {e}")
    
    def _build_prompt(self, text: str, template: Template) -> str:
        """
        Build extraction prompt with template schema.
        
        Args:
            text: Legal case text
            template: Template object
            
        Returns:
            Formatted prompt string
        """
        # Format schema as readable JSON
        schema_str = json.dumps(template.schema, indent=2)
        
        return self.FACT_EXTRACTION_PROMPT_TEMPLATE.format(
            template_label=template.label,
            schema=schema_str,
            text=text
        )
    
    def _parse_response(self, response_text: str) -> Dict[str, Any]:
        """
        Parse LLM response into facts dictionary.
        
        Args:
            response_text: JSON response from LLM
            
        Returns:
            Parsed facts dictionary with 4 tiers
        """
        try:
            # Extract JSON from response
            if "```json" in response_text:
                start = response_text.find("```json") + 7
                end = response_text.find("```", start)
                response_text = response_text[start:end].strip()
            elif "```" in response_text:
                start = response_text.find("```") + 3
                end = response_text.find("```", start)
                response_text = response_text[start:end].strip()
            
            facts = json.loads(response_text)
            
            # Ensure all tiers exist
            default_facts = {
                'tier_1_parties': {},
                'tier_2_incident': {},
                'tier_3_legal': {},
                'tier_4_procedural': {}
            }
            
            for tier in default_facts:
                if tier not in facts:
                    facts[tier] = default_facts[tier]
            
            return facts
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            logger.debug(f"Response text: {response_text}")
            # Return empty facts structure
            return {
                'tier_1_parties': {},
                'tier_2_incident': {},
                'tier_3_legal': {},
                'tier_4_procedural': {}
            }
