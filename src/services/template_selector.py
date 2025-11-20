"""
Template selection service based on legal ontology matching.
Implements ITemplateSelector interface.
"""

import logging
import json
from typing import Dict, Any
from pathlib import Path

from core.interfaces import ITemplateSelector
from core.models import Template
from core.exceptions import TemplateNotFoundError
from core.config import Config

logger = logging.getLogger(__name__)


class TemplateSelector(ITemplateSelector):
    """
    Select appropriate fact extraction template based on case metadata.
    Uses ontology-based matching of legal sections.
    """
    
    def __init__(self):
        """Initialize template selector with ontology and templates."""
        self.config = Config()
        self.ontology = self._load_ontology()
        self.templates = self._load_templates()
        logger.info(f"Template selector initialized with {len(self.templates)} templates")
    
    def _load_ontology(self) -> Dict[str, Any]:
        """Load legal ontology schema."""
        try:
            ontology_path = self.config.ontology_path
            if not ontology_path.exists():
                logger.warning(f"Ontology file not found: {ontology_path}")
                return {}
            
            with open(ontology_path, 'r', encoding='utf-8') as f:
                ontology = json.load(f)
            
            logger.info(f"Loaded ontology from {ontology_path}")
            return ontology
            
        except Exception as e:
            logger.error(f"Failed to load ontology: {e}")
            return {}
    
    def _load_templates(self) -> Dict[str, Template]:
        """Load all fact extraction templates."""
        templates = {}
        
        try:
            templates_dir = self.config.templates_dir
            if not templates_dir.exists():
                logger.warning(f"Templates directory not found: {templates_dir}")
                return templates
            
            # Load each template file
            for template_file in templates_dir.glob("*.json"):
                if template_file.name == "templates.json":
                    continue  # Skip index file
                
                try:
                    with open(template_file, 'r', encoding='utf-8') as f:
                        template_data = json.load(f)
                    
                    template_id = template_file.stem
                    templates[template_id] = template_data
                    
                except Exception as e:
                    logger.warning(f"Failed to load template {template_file}: {e}")
            
            logger.info(f"Loaded {len(templates)} templates")
            return templates
            
        except Exception as e:
            logger.error(f"Failed to load templates: {e}")
            return {}
    
    def select(self, metadata: Dict[str, Any]) -> Template:
        """
        Select most appropriate template based on metadata.
        
        Args:
            metadata: Case metadata with sections_invoked
            
        Returns:
            Selected Template object
            
        Raises:
            TemplateNotFoundError: If no suitable template found
        """
        try:
            sections = metadata.get('sections_invoked', [])
            most_appropriate = metadata.get('most_appropriate_section', '')
            
            # Priority: use most_appropriate_section if available
            if most_appropriate and most_appropriate != 'Unknown':
                template_id = self._match_section_to_template(most_appropriate)
                if template_id:
                    return self._create_template(template_id, 1.0)
            
            # Fallback: match against all invoked sections
            if sections:
                for section in sections:
                    template_id = self._match_section_to_template(section)
                    if template_id:
                        confidence = 0.8  # Lower confidence for non-primary section
                        return self._create_template(template_id, confidence)
            
            # Default: use generic legal case template
            logger.warning("No specific template matched, using generic template")
            return self._create_template("legal_case", 0.5)
            
        except Exception as e:
            logger.error(f"Template selection failed: {e}")
            raise TemplateNotFoundError(f"Failed to select template: {e}")
    
    def _match_section_to_template(self, section: str) -> str:
        """
        Match legal section to template ID.
        
        Args:
            section: Legal section (e.g., "IPC 302", "IPC 376")
            
        Returns:
            Template ID or empty string if no match
        """
        # Normalize section
        section_normalized = section.lower().replace(' ', '_')
        
        # Direct mapping for IPC sections
        ipc_mappings = {
            'ipc_302': 'ipc_302',
            'ipc_304': 'ipc_304_p2',
            'ipc_306': 'ipc_306',
            'ipc_307': 'ipc_307',
            'ipc_316': 'ipc_316',
            'ipc_320': 'ipc_320',
            'ipc_323': 'ipc_323',
            'ipc_324': 'ipc_324',
            'ipc_354': 'ipc_354',
            'ipc_354a': 'ipc_354a',
            'ipc_363': 'ipc_363',
            'ipc_376': 'ipc_376',
            'ipc_379': 'ipc_379',
            'ipc_380': 'ipc_380',
            'ipc_384': 'ipc_384',
            'ipc_392': 'ipc_392',
            'ipc_394': 'ipc_394',
            'ipc_395': 'ipc_395',
            'ipc_397': 'ipc_397',
            'ipc_399': 'ipc_399',
            'ipc_402': 'ipc_402',
            'ipc_427': 'ipc_427',
            'ipc_452': 'ipc_452',
            'ipc_457': 'ipc_457',
            'ipc_498a': 'ipc_498a',
        }
        
        # Check direct mappings
        for pattern, template_id in ipc_mappings.items():
            if pattern in section_normalized:
                if template_id in self.templates:
                    return template_id
        
        # Category-based fallback
        if any(word in section_normalized for word in ['murder', '302']):
            return 'ipc_302'
        elif any(word in section_normalized for word in ['rape', 'sexual', '376', '354']):
            return 'sexual_offense'
        elif any(word in section_normalized for word in ['theft', '379', '380']):
            return 'theft'
        elif any(word in section_normalized for word in ['robbery', '392', '394', '395']):
            return 'robbery'
        elif any(word in section_normalized for word in ['assault', '323', '324']):
            return 'assault'
        elif any(word in section_normalized for word in ['498a', 'domestic']):
            return 'ipc_498a'
        
        return ''
    
    def _create_template(self, template_id: str, confidence: float) -> Template:
        """
        Create Template object from template ID.
        
        Args:
            template_id: Template identifier
            confidence: Confidence score for match
            
        Returns:
            Template object
        """
        if template_id not in self.templates:
            # Fallback to legal_case if specific template not found
            template_id = 'legal_case'
            confidence = 0.3
        
        template_data = self.templates.get(template_id, {})
        
        return Template(
            template_id=template_id,
            label=template_data.get('label', template_id.replace('_', ' ').title()),
            schema=template_data.get('schema', {}),
            confidence_score=confidence
        )
