"""
Case Storage Module
Stores processed legal case data in structured JSON format.
"""
import json
import logging
import os
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
import hashlib

@dataclass
class ProcessedCase:
    """Complete processed case data structure."""
    case_id: str
    processing_timestamp: str
    source_file: str
    metadata: Dict[str, Any]
    ontology_matches: List[Dict[str, Any]]
    selected_template: str
    extracted_facts: Dict[str, Any]
    processing_summary: Dict[str, Any]
    
    def __post_init__(self):
        if not self.processing_timestamp:
            self.processing_timestamp = datetime.now().isoformat()
        if not self.case_id:
            self.case_id = self._generate_case_id()
    
    def _generate_case_id(self) -> str:
        """Generate unique case ID based on metadata."""
        # Use case number if available, otherwise generate hash
        if self.metadata and self.metadata.get('case_number'):
            case_num = self.metadata['case_number']
            # Clean case number for use as ID
            case_id = ''.join(c for c in case_num if c.isalnum() or c in '-_')
            return case_id
        else:
            # Generate hash-based ID
            content = f"{self.source_file}_{self.processing_timestamp}"
            return hashlib.md5(content.encode()).hexdigest()[:12]

class CaseStorage:
    """Manages storage of processed legal cases."""
    
    def __init__(self, storage_dir: str = "cases/processed"):
        """
        Initialize case storage.
        
        Args:
            storage_dir (str): Directory to store processed cases
        """
        self.logger = logging.getLogger(__name__)
        self.storage_dir = Path(storage_dir)
        
        # Create storage directory structure
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        (self.storage_dir / "cases").mkdir(exist_ok=True)
        (self.storage_dir / "index").mkdir(exist_ok=True)
        (self.storage_dir / "metadata").mkdir(exist_ok=True)
        
        self.logger.info(f"Case storage initialized: {storage_dir}")
    
    def store_case(self, source_file: str, metadata: Dict[str, Any], 
                   ontology_matches: List[Dict[str, Any]], selected_template: str,
                   extracted_facts: Dict[str, Any]) -> ProcessedCase:
        """
        Store a complete processed case.
        
        Args:
            source_file (str): Path to original PDF file
            metadata (Dict): Extracted case metadata
            ontology_matches (List): Ontology matching results
            selected_template (str): Template ID used for extraction
            extracted_facts (Dict): Extracted facts from template
            
        Returns:
            ProcessedCase: Stored case object
        """
        try:
            # Create processing summary
            processing_summary = self._create_processing_summary(
                metadata, ontology_matches, selected_template, extracted_facts
            )
            
            # Create ProcessedCase object
            processed_case = ProcessedCase(
                case_id="",  # Will be generated in __post_init__
                processing_timestamp=datetime.now().isoformat(),
                source_file=os.path.abspath(source_file),
                metadata=metadata,
                ontology_matches=ontology_matches,
                selected_template=selected_template,
                extracted_facts=extracted_facts,
                processing_summary=processing_summary
            )
            
            # Save case data
            case_path = self._save_case_data(processed_case)
            
            # Update index
            self._update_case_index(processed_case)
            
            # Save metadata separately for quick access
            self._save_case_metadata(processed_case)
            
            self.logger.info(f"Case stored successfully: {processed_case.case_id}")
            return processed_case
            
        except Exception as e:
            self.logger.error(f"Error storing case: {e}")
            raise
    
    def _create_processing_summary(self, metadata: Dict[str, Any], 
                                 ontology_matches: List[Dict[str, Any]],
                                 selected_template: str, 
                                 extracted_facts: Dict[str, Any]) -> Dict[str, Any]:
        """Create processing summary statistics."""
        summary = {
            'metadata_fields_extracted': len([v for v in metadata.values() if v is not None]),
            'total_metadata_fields': len(metadata),
            'ontology_matches_found': len(ontology_matches),
            'best_match_confidence': max([m.get('confidence_score', 0) for m in ontology_matches], default=0),
            'template_used': selected_template,
            'extraction_confidence': extracted_facts.get('extraction_confidence', 0),
            'total_facts_extracted': self._count_extracted_facts(extracted_facts),
            'facts_by_tier': self._count_facts_by_tier(extracted_facts),
            'residual_facts_count': len(extracted_facts.get('residual_facts', [])),
            'processing_status': 'completed'
        }
        
        return summary
    
    def _count_extracted_facts(self, extracted_facts: Dict[str, Any]) -> int:
        """Count total number of extracted facts."""
        count = 0
        for tier in ['tier_1_facts', 'tier_2_facts', 'tier_3_facts', 'tier_4_facts']:
            tier_facts = extracted_facts.get(tier, {})
            count += len([v for v in tier_facts.values() if v is not None])
        return count
    
    def _count_facts_by_tier(self, extracted_facts: Dict[str, Any]) -> Dict[str, int]:
        """Count facts by tier."""
        tier_counts = {}
        tier_mapping = {
            'tier_1_facts': 'tier_1_determinative',
            'tier_2_facts': 'tier_2_material',
            'tier_3_facts': 'tier_3_contextual',
            'tier_4_facts': 'tier_4_procedural'
        }
        
        for fact_key, tier_name in tier_mapping.items():
            tier_facts = extracted_facts.get(fact_key, {})
            tier_counts[tier_name] = len([v for v in tier_facts.values() if v is not None])
        
        return tier_counts
    
    def _save_case_data(self, processed_case: ProcessedCase) -> str:
        """Save complete case data to JSON file."""
        case_filename = f"{processed_case.case_id}.json"
        case_path = self.storage_dir / "cases" / case_filename
        
        # Convert to dictionary and save
        case_data = asdict(processed_case)
        
        with open(case_path, 'w', encoding='utf-8') as f:
            json.dump(case_data, f, indent=2, ensure_ascii=False)
        
        self.logger.info(f"Case data saved: {case_path}")
        return str(case_path)
    
    def _update_case_index(self, processed_case: ProcessedCase) -> None:
        """Update the master case index."""
        index_path = self.storage_dir / "index" / "case_index.json"
        
        # Load existing index
        if index_path.exists():
            with open(index_path, 'r', encoding='utf-8') as f:
                index_data = json.load(f)
        else:
            index_data = {
                'total_cases': 0,
                'cases': [],
                'last_updated': None
            }
        
        # Create index entry
        index_entry = {
            'case_id': processed_case.case_id,
            'case_number': processed_case.metadata.get('case_number'),
            'case_title': processed_case.metadata.get('case_title'),
            'court_name': processed_case.metadata.get('court_name'),
            'sections_invoked': processed_case.metadata.get('sections_invoked', []),
            'template_used': processed_case.selected_template,
            'processing_timestamp': processed_case.processing_timestamp,
            'extraction_confidence': processed_case.extracted_facts.get('extraction_confidence', 0),
            'source_file': processed_case.source_file
        }
        
        # Add or update entry
        existing_index = next((i for i, case in enumerate(index_data['cases']) 
                              if case['case_id'] == processed_case.case_id), None)
        
        if existing_index is not None:
            index_data['cases'][existing_index] = index_entry
        else:
            index_data['cases'].append(index_entry)
            index_data['total_cases'] += 1
        
        index_data['last_updated'] = datetime.now().isoformat()
        
        # Save updated index
        with open(index_path, 'w', encoding='utf-8') as f:
            json.dump(index_data, f, indent=2, ensure_ascii=False)
    
    def _save_case_metadata(self, processed_case: ProcessedCase) -> None:
        """Save case metadata separately for quick lookups."""
        metadata_filename = f"{processed_case.case_id}_metadata.json"
        metadata_path = self.storage_dir / "metadata" / metadata_filename
        
        metadata_summary = {
            'case_id': processed_case.case_id,
            'metadata': processed_case.metadata,
            'template_used': processed_case.selected_template,
            'processing_summary': processed_case.processing_summary,
            'extraction_timestamp': processed_case.processing_timestamp
        }
        
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata_summary, f, indent=2, ensure_ascii=False)
    
    def load_case(self, case_id: str) -> Optional[ProcessedCase]:
        """
        Load a processed case by ID.
        
        Args:
            case_id (str): Case ID to load
            
        Returns:
            Optional[ProcessedCase]: Loaded case or None if not found
        """
        try:
            case_path = self.storage_dir / "cases" / f"{case_id}.json"
            
            if not case_path.exists():
                self.logger.warning(f"Case not found: {case_id}")
                return None
            
            with open(case_path, 'r', encoding='utf-8') as f:
                case_data = json.load(f)
            
            # Convert back to ProcessedCase object
            processed_case = ProcessedCase(**case_data)
            
            return processed_case
            
        except Exception as e:
            self.logger.error(f"Error loading case {case_id}: {e}")
            return None
    
    def search_cases(self, **search_criteria) -> List[Dict[str, Any]]:
        """
        Search cases by various criteria.
        
        Args:
            **search_criteria: Search parameters (e.g., template_used, court_name, etc.)
            
        Returns:
            List[Dict]: List of matching case summaries
        """
        try:
            index_path = self.storage_dir / "index" / "case_index.json"
            
            if not index_path.exists():
                return []
            
            with open(index_path, 'r', encoding='utf-8') as f:
                index_data = json.load(f)
            
            matching_cases = []
            
            for case_entry in index_data.get('cases', []):
                match = True
                
                for criteria_key, criteria_value in search_criteria.items():
                    case_value = case_entry.get(criteria_key)
                    
                    if criteria_key == 'sections_invoked' and isinstance(criteria_value, str):
                        # Special handling for sections
                        if not any(criteria_value.upper() in section.upper() 
                                 for section in case_entry.get('sections_invoked', [])):
                            match = False
                            break
                    elif case_value != criteria_value:
                        match = False
                        break
                
                if match:
                    matching_cases.append(case_entry)
            
            self.logger.info(f"Found {len(matching_cases)} matching cases")
            return matching_cases
            
        except Exception as e:
            self.logger.error(f"Error searching cases: {e}")
            return []
    
    def get_all_cases(self) -> List[Dict[str, Any]]:
        """Get all processed cases summary."""
        try:
            index_path = self.storage_dir / "index" / "case_index.json"
            
            if not index_path.exists():
                return []
            
            with open(index_path, 'r', encoding='utf-8') as f:
                index_data = json.load(f)
            
            return index_data.get('cases', [])
            
        except Exception as e:
            self.logger.error(f"Error getting all cases: {e}")
            return []
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get storage statistics."""
        try:
            all_cases = self.get_all_cases()
            
            if not all_cases:
                return {'total_cases': 0}
            
            # Calculate statistics
            templates_used = {}
            courts = {}
            sections = {}
            confidence_scores = []
            
            for case in all_cases:
                # Template usage
                template = case.get('template_used', 'unknown')
                templates_used[template] = templates_used.get(template, 0) + 1
                
                # Court distribution
                court = case.get('court_name', 'unknown')
                courts[court] = courts.get(court, 0) + 1
                
                # Sections distribution
                for section in case.get('sections_invoked', []):
                    sections[section] = sections.get(section, 0) + 1
                
                # Confidence scores
                confidence = case.get('extraction_confidence', 0)
                if confidence > 0:
                    confidence_scores.append(confidence)
            
            stats = {
                'total_cases': len(all_cases),
                'templates_used': templates_used,
                'courts_distribution': courts,
                'sections_distribution': sections,
                'average_confidence': sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0,
                'high_confidence_cases': len([c for c in confidence_scores if c >= 0.7]),
                'low_confidence_cases': len([c for c in confidence_scores if c < 0.5])
            }
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Error calculating statistics: {e}")
            return {'error': str(e)}
    
    def export_cases(self, output_path: str, case_ids: Optional[List[str]] = None) -> None:
        """
        Export cases to a single JSON file.
        
        Args:
            output_path (str): Path to export file
            case_ids (Optional[List[str]]): Specific case IDs to export, None for all
        """
        try:
            if case_ids is None:
                # Export all cases
                case_summaries = self.get_all_cases()
                case_ids = [case['case_id'] for case in case_summaries]
            
            exported_cases = []
            
            for case_id in case_ids:
                case_data = self.load_case(case_id)
                if case_data:
                    exported_cases.append(asdict(case_data))
            
            export_data = {
                'export_timestamp': datetime.now().isoformat(),
                'total_cases': len(exported_cases),
                'cases': exported_cases
            }
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"Exported {len(exported_cases)} cases to {output_path}")
            
        except Exception as e:
            self.logger.error(f"Error exporting cases: {e}")
            raise

def main():
    """Example usage of case storage."""
    storage = CaseStorage()
    
    # Example case data
    sample_metadata = {
        'case_number': 'CR123/2023',
        'case_title': 'Sample Case',
        'court_name': 'Sample Court',
        'sections_invoked': ['IPC 376']
    }
    
    sample_matches = [
        {'node_id': 'ipc_376', 'confidence_score': 0.9}
    ]
    
    sample_facts = {
        'template_id': 'ipc_376',
        'tier_1_facts': {'victim_age': 25},
        'tier_2_facts': {},
        'tier_3_facts': {},
        'tier_4_facts': {},
        'residual_facts': [],
        'extraction_confidence': 0.8
    }
    
    # Store case
    processed_case = storage.store_case(
        source_file="sample.pdf",
        metadata=sample_metadata,
        ontology_matches=sample_matches,
        selected_template="ipc_376",
        extracted_facts=sample_facts
    )
    
    print(f"Stored case: {processed_case.case_id}")
    
    # Get statistics
    stats = storage.get_statistics()
    print(f"Storage statistics: {json.dumps(stats, indent=2)}")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()