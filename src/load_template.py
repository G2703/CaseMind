"""
Template Loader Module
Loads appropriate templates based on ontology matching results.
"""
import json
import logging
from typing import Dict, List, Optional, Any
from pathlib import Path
from dataclasses import dataclass

@dataclass
class Template:
    """Represents a loaded template."""
    node_id: str
    label: str
    parent: Optional[str]
    sections: List[str]
    fact_tiers: Dict[str, Dict[str, List[str]]]
    field_definitions: Dict[str, Dict[str, str]]
    example_terms: List[str]
    residual_details: Dict[str, List[str]]
    suggested_section_mapping_confidence: float

class TemplateLoader:
    """Loads and manages legal case templates."""
    
    def __init__(self, templates_dir: str = "templates"):
        """
        Initialize template loader.
        
        Args:
            templates_dir (str): Directory containing template JSON files
        """
        self.logger = logging.getLogger(__name__)
        self.templates_dir = Path(templates_dir)
        
        if not self.templates_dir.exists():
            raise FileNotFoundError(f"Templates directory not found: {templates_dir}")
        
        self.logger.info(f"Template loader initialized with directory: {templates_dir}")
    
    def load_template(self, node_id: str) -> Optional[Template]:
        """
        Load template for a specific node ID.
        
        Args:
            node_id (str): Node ID from ontology
            
        Returns:
            Template: Loaded template object, None if not found
        """
        try:
            template_path = self.templates_dir / f"{node_id}.json"
            
            if not template_path.exists():
                self.logger.warning(f"Template file not found: {template_path}")
                return None
            
            with open(template_path, 'r', encoding='utf-8') as f:
                template_data = json.load(f)
            
            # Validate required fields
            required_fields = ['node_id', 'label', 'fact_tiers', 'field_definitions']
            for field in required_fields:
                if field not in template_data:
                    raise ValueError(f"Missing required field '{field}' in template {node_id}")
            
            # Create Template object
            template = Template(
                node_id=template_data['node_id'],
                label=template_data['label'],
                parent=template_data.get('parent'),
                sections=template_data.get('sections', []),
                fact_tiers=template_data.get('fact_tiers', {}),
                field_definitions=template_data.get('field_definitions', {}),
                example_terms=template_data.get('example_terms', []),
                residual_details=template_data.get('residual_details', {'unclassified_facts': []}),
                suggested_section_mapping_confidence=template_data.get('suggested_section_mapping_confidence', 1.0)
            )
            
            self.logger.info(f"Successfully loaded template for {node_id}")
            return template
            
        except Exception as e:
            self.logger.error(f"Error loading template for {node_id}: {e}")
            return None
    
    def load_multiple_templates(self, node_ids: List[str]) -> Dict[str, Template]:
        """
        Load multiple templates.
        
        Args:
            node_ids (List[str]): List of node IDs
            
        Returns:
            Dict[str, Template]: Dictionary of node_id -> Template
        """
        templates = {}
        
        for node_id in node_ids:
            template = self.load_template(node_id)
            if template:
                templates[node_id] = template
        
        self.logger.info(f"Loaded {len(templates)} templates out of {len(node_ids)} requested")
        return templates
    
    def get_all_fields(self, template: Template) -> Dict[str, Dict[str, str]]:
        """
        Get all fields from all tiers with their definitions.
        
        Args:
            template (Template): Template object
            
        Returns:
            Dict[str, Dict[str, str]]: Field name -> field definition
        """
        all_fields = {}
        
        # Extract fields from all tiers
        for tier_name, tier_data in template.fact_tiers.items():
            fields = tier_data.get('fields', [])
            for field in fields:
                if field in template.field_definitions:
                    all_fields[field] = template.field_definitions[field].copy()
                    all_fields[field]['tier'] = tier_name
        
        return all_fields
    
    def get_fields_by_tier(self, template: Template, tier_name: str) -> List[str]:
        """
        Get fields for a specific tier.
        
        Args:
            template (Template): Template object
            tier_name (str): Name of the tier (e.g., 'tier_1_determinative')
            
        Returns:
            List[str]: List of field names in the tier
        """
        tier_data = template.fact_tiers.get(tier_name, {})
        return tier_data.get('fields', [])
    
    def get_required_fields(self, template: Template) -> List[str]:
        """
        Get required fields (typically from tier 1 and tier 2).
        
        Args:
            template (Template): Template object
            
        Returns:
            List[str]: List of required field names
        """
        required_fields = []
        
        # Tier 1 and Tier 2 are typically required
        tier1_fields = self.get_fields_by_tier(template, 'tier_1_determinative')
        tier2_fields = self.get_fields_by_tier(template, 'tier_2_material')
        
        required_fields.extend(tier1_fields)
        required_fields.extend(tier2_fields)
        
        return list(set(required_fields))  # Remove duplicates
    
    def get_optional_fields(self, template: Template) -> List[str]:
        """
        Get optional fields (typically from tier 3 and tier 4).
        
        Args:
            template (Template): Template object
            
        Returns:
            List[str]: List of optional field names
        """
        optional_fields = []
        
        # Tier 3 and Tier 4 are typically optional
        tier3_fields = self.get_fields_by_tier(template, 'tier_3_contextual')
        tier4_fields = self.get_fields_by_tier(template, 'tier_4_procedural')
        
        optional_fields.extend(tier3_fields)
        optional_fields.extend(tier4_fields)
        
        return list(set(optional_fields))  # Remove duplicates
    
    def create_extraction_schema(self, template: Template) -> Dict[str, Any]:
        """
        Create a schema for fact extraction based on template with tier structure.
        
        Args:
            template (Template): Template object
            
        Returns:
            Dict[str, Any]: Schema for fact extraction
        """
        schema = {
            'template_id': template.node_id,
            'template_label': template.label,
            'sections': template.sections,
            'fact_tiers': template.fact_tiers,
            'field_definitions': template.field_definitions,
            'example_terms': template.example_terms,
            'extraction_instructions': {
                'focus_sections': template.sections,
                'example_terms': template.example_terms,
                'confidence_threshold': template.suggested_section_mapping_confidence
            }
        }
        
        # Build required and optional field mappings for backward compatibility
        required_fields = {}
        optional_fields = {}
        
        # Tier 1 and 2 are typically required (critical for case determination)
        critical_tiers = ['tier_1_determinative', 'tier_2_material']
        optional_tiers = ['tier_3_contextual', 'tier_4_procedural']
        
        for tier_name, tier_info in template.fact_tiers.items():
            tier_fields = tier_info.get('fields', [])
            
            for field in tier_fields:
                if field in template.field_definitions:
                    field_def = template.field_definitions[field].copy()
                    field_def['tier'] = tier_name
                    
                    if tier_name in critical_tiers:
                        required_fields[field] = field_def
                    else:
                        optional_fields[field] = field_def
        
        schema['required_fields'] = required_fields
        schema['optional_fields'] = optional_fields
        
        return schema
    
    def merge_templates(self, templates: List[Template]) -> Template:
        """
        Merge multiple templates into a combined template.
        Useful when a case matches multiple offense types.
        
        Args:
            templates (List[Template]): List of templates to merge
            
        Returns:
            Template: Merged template
        """
        if not templates:
            raise ValueError("No templates provided for merging")
        
        if len(templates) == 1:
            return templates[0]
        
        # Start with first template
        merged = templates[0]
        
        # Create a new merged template
        merged_node_id = "_".join([t.node_id for t in templates])
        merged_label = " + ".join([t.label for t in templates])
        
        merged_sections = []
        merged_fact_tiers = {
            'tier_1_determinative': {'fields': []},
            'tier_2_material': {'fields': []},
            'tier_3_contextual': {'fields': []},
            'tier_4_procedural': {'fields': []}
        }
        merged_field_definitions = {}
        merged_example_terms = []
        
        # Merge data from all templates
        for template in templates:
            merged_sections.extend(template.sections)
            merged_example_terms.extend(template.example_terms)
            merged_field_definitions.update(template.field_definitions)
            
            # Merge fact tiers
            for tier_name, tier_data in template.fact_tiers.items():
                if tier_name in merged_fact_tiers:
                    merged_fact_tiers[tier_name]['fields'].extend(tier_data.get('fields', []))
        
        # Remove duplicates
        merged_sections = list(set(merged_sections))
        merged_example_terms = list(set(merged_example_terms))
        
        for tier_name in merged_fact_tiers:
            merged_fact_tiers[tier_name]['fields'] = list(set(merged_fact_tiers[tier_name]['fields']))
        
        # Create merged template
        merged_template = Template(
            node_id=merged_node_id,
            label=merged_label,
            parent=None,  # Merged templates don't have a single parent
            sections=merged_sections,
            fact_tiers=merged_fact_tiers,
            field_definitions=merged_field_definitions,
            example_terms=merged_example_terms,
            residual_details={'unclassified_facts': []},
            suggested_section_mapping_confidence=min([t.suggested_section_mapping_confidence for t in templates])
        )
        
        self.logger.info(f"Merged {len(templates)} templates into {merged_node_id}")
        return merged_template
    
    def list_available_templates(self) -> List[str]:
        """
        List all available template files.
        
        Returns:
            List[str]: List of available template node IDs
        """
        template_files = list(self.templates_dir.glob("*.json"))
        node_ids = [f.stem for f in template_files]
        
        self.logger.info(f"Found {len(node_ids)} available templates")
        return node_ids
    
    def validate_template(self, template: Template) -> Dict[str, Any]:
        """
        Validate template structure and consistency.
        
        Args:
            template (Template): Template to validate
            
        Returns:
            Dict[str, Any]: Validation results
        """
        validation_results = {
            'is_valid': True,
            'errors': [],
            'warnings': []
        }
        
        # Check if all fields in tiers have definitions
        all_tier_fields = set()
        for tier_data in template.fact_tiers.values():
            all_tier_fields.update(tier_data.get('fields', []))
        
        defined_fields = set(template.field_definitions.keys())
        
        # Find missing definitions
        missing_definitions = all_tier_fields - defined_fields
        if missing_definitions:
            validation_results['errors'].append(f"Missing field definitions: {missing_definitions}")
            validation_results['is_valid'] = False
        
        # Find unused definitions
        unused_definitions = defined_fields - all_tier_fields
        if unused_definitions:
            validation_results['warnings'].append(f"Unused field definitions: {unused_definitions}")
        
        # Check for empty tiers
        empty_tiers = [tier for tier, data in template.fact_tiers.items() 
                      if not data.get('fields')]
        if empty_tiers:
            validation_results['warnings'].append(f"Empty tiers: {empty_tiers}")
        
        return validation_results

def main():
    """Example usage of template loader."""
    loader = TemplateLoader("templates")
    
    # List available templates
    available = loader.list_available_templates()
    print(f"Available templates: {available[:5]}...")  # Show first 5
    
    # Load a specific template
    if 'ipc_376' in available:
        template = loader.load_template('ipc_376')
        if template:
            print(f"\nLoaded template: {template.label}")
            
            # Get extraction schema
            schema = loader.create_extraction_schema(template)
            print(f"Required fields: {list(schema['required_fields'].keys())}")
            print(f"Optional fields: {list(schema['optional_fields'].keys())}")
            
            # Validate template
            validation = loader.validate_template(template)
            print(f"Template validation: {validation}")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()