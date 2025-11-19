"""
Ontology Matcher Module
Compares extracted metadata with ontology schema to identify relevant templates.
"""
import json
import logging
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path
import re
from dataclasses import dataclass
from collections import defaultdict

@dataclass
class MatchResult:
    """Result of ontology matching."""
    node_id: str
    label: str
    confidence_score: float
    matching_sections: List[str]
    matching_terms: List[str]
    parent_path: List[str]

class OntologyMatcher:
    """Matches case metadata against ontology schema to find relevant templates."""
    
    def __init__(self, ontology_path: str = "Ontology_schema/ontology_schema.json"):
        """
        Initialize ontology matcher.
        
        Args:
            ontology_path (str): Path to ontology schema JSON file
        """
        self.logger = logging.getLogger(__name__)
        self.ontology_path = ontology_path
        self.ontology = self._load_ontology()
        self.section_to_node_map = self._build_section_mapping()
        self.term_to_node_map = self._build_term_mapping()
        
    def _load_ontology(self) -> Dict[str, Any]:
        """Load ontology schema from JSON file."""
        try:
            with open(self.ontology_path, 'r', encoding='utf-8') as f:
                ontology_data = json.load(f)
            
            # Convert list to dict for easier lookup
            ontology_dict = {}
            for node in ontology_data.get('ontology_schema', []):
                ontology_dict[node['node_id']] = node
            
            self.logger.info(f"Loaded ontology with {len(ontology_dict)} nodes")
            return ontology_dict
            
        except Exception as e:
            self.logger.error(f"Error loading ontology from {self.ontology_path}: {e}")
            raise
    
    def _build_section_mapping(self) -> Dict[str, List[str]]:
        """Build mapping from legal sections to ontology nodes."""
        section_map = defaultdict(list)
        
        for node_id, node_data in self.ontology.items():
            sections = node_data.get('sections', [])
            for section in sections:
                # Normalize section format
                normalized_section = self._normalize_section(section)
                section_map[normalized_section].append(node_id)
        
        return dict(section_map)
    
    def _build_term_mapping(self) -> Dict[str, List[str]]:
        """Build mapping from example terms to ontology nodes."""
        term_map = defaultdict(list)
        
        for node_id, node_data in self.ontology.items():
            example_terms = node_data.get('example_terms', [])
            for term in example_terms:
                # Normalize term
                normalized_term = term.lower().strip()
                term_map[normalized_term].append(node_id)
        
        return dict(term_map)
    
    def _normalize_section(self, section: str) -> str:
        """Normalize legal section format for consistent matching."""
        # Remove extra spaces and convert to uppercase
        section = section.strip().upper()
        
        # Standardize format: "IPC 376" instead of "IPC376" or "Section 376 IPC"
        section = re.sub(r'\s+', ' ', section)
        section = re.sub(r'SECTION\s+(\d+[A-Z]*)\s+IPC', r'IPC \1', section)
        section = re.sub(r'IPC(\d+)', r'IPC \1', section)
        section = re.sub(r'POCSO(\d+)', r'POCSO \1', section)
        
        return section
    
    def find_matching_nodes(self, metadata: Dict[str, Any], case_text: str = "") -> List[MatchResult]:
        """
        Find ontology nodes that match the case metadata.
        
        Args:
            metadata (Dict): Extracted case metadata
            case_text (str): Full case text for term matching
            
        Returns:
            List[MatchResult]: List of matching nodes with confidence scores
        """
        matches = []
        
        try:
            # Extract sections from metadata
            sections_invoked = metadata.get('sections_invoked', [])
            
            # 1. Primary matching by legal sections
            section_matches = self._match_by_sections(sections_invoked)
            matches.extend(section_matches)
            
            # 2. Secondary matching by example terms in case text
            if case_text:
                term_matches = self._match_by_terms(case_text)
                matches.extend(term_matches)
            
            # 3. Fallback matching by case type and court
            if not matches:
                fallback_matches = self._fallback_matching(metadata)
                matches.extend(fallback_matches)
            
            # Remove duplicates and sort by confidence
            unique_matches = self._deduplicate_matches(matches)
            unique_matches.sort(key=lambda x: x.confidence_score, reverse=True)
            
            self.logger.info(f"Found {len(unique_matches)} matching nodes")
            return unique_matches
            
        except Exception as e:
            self.logger.error(f"Error finding matching nodes: {e}")
            return []
    
    def _match_by_sections(self, sections_invoked: List[str]) -> List[MatchResult]:
        """Match ontology nodes by legal sections."""
        matches = []
        
        for section in sections_invoked:
            normalized_section = self._normalize_section(section)
            
            if normalized_section in self.section_to_node_map:
                matching_nodes = self.section_to_node_map[normalized_section]
                
                for node_id in matching_nodes:
                    node_data = self.ontology[node_id]
                    
                    # High confidence for exact section matches
                    confidence = 0.9
                    
                    # Get parent path
                    parent_path = self._get_parent_path(node_id)
                    
                    match_result = MatchResult(
                        node_id=node_id,
                        label=node_data['label'],
                        confidence_score=confidence,
                        matching_sections=[section],
                        matching_terms=[],
                        parent_path=parent_path
                    )
                    matches.append(match_result)
        
        return matches
    
    def _match_by_terms(self, case_text: str) -> List[MatchResult]:
        """Match ontology nodes by example terms found in case text."""
        matches = []
        case_text_lower = case_text.lower()
        
        for term, node_ids in self.term_to_node_map.items():
            if term in case_text_lower:
                for node_id in node_ids:
                    node_data = self.ontology[node_id]
                    
                    # Medium confidence for term matches
                    confidence = 0.6
                    
                    # Boost confidence if multiple terms match
                    matching_terms = [t for t in node_data.get('example_terms', []) 
                                    if t.lower() in case_text_lower]
                    
                    if len(matching_terms) > 1:
                        confidence += 0.1 * (len(matching_terms) - 1)
                        confidence = min(confidence, 0.85)  # Cap at 0.85
                    
                    parent_path = self._get_parent_path(node_id)
                    
                    match_result = MatchResult(
                        node_id=node_id,
                        label=node_data['label'],
                        confidence_score=confidence,
                        matching_sections=[],
                        matching_terms=matching_terms,
                        parent_path=parent_path
                    )
                    matches.append(match_result)
        
        return matches
    
    def _fallback_matching(self, metadata: Dict[str, Any]) -> List[MatchResult]:
        """Fallback matching when no direct matches found."""
        matches = []
        
        case_type = metadata.get('case_type', '').lower()
        
        # Basic categorization based on case type
        if 'criminal' in case_type or 'crl' in case_type:
            # Default to criminal_case node
            if 'criminal_case' in self.ontology:
                node_data = self.ontology['criminal_case']
                parent_path = self._get_parent_path('criminal_case')
                
                match_result = MatchResult(
                    node_id='criminal_case',
                    label=node_data['label'],
                    confidence_score=0.3,  # Low confidence
                    matching_sections=[],
                    matching_terms=[],
                    parent_path=parent_path
                )
                matches.append(match_result)
        
        elif 'civil' in case_type or 'family' in case_type:
            # Default to family_law_dispute node
            if 'family_law_dispute' in self.ontology:
                node_data = self.ontology['family_law_dispute']
                parent_path = self._get_parent_path('family_law_dispute')
                
                match_result = MatchResult(
                    node_id='family_law_dispute',
                    label=node_data['label'],
                    confidence_score=0.3,
                    matching_sections=[],
                    matching_terms=[],
                    parent_path=parent_path
                )
                matches.append(match_result)
        
        return matches
    
    def _get_parent_path(self, node_id: str) -> List[str]:
        """Get the path from root to the given node."""
        path = []
        current_id = node_id
        
        while current_id and current_id in self.ontology:
            node_data = self.ontology[current_id]
            path.insert(0, node_data['label'])
            current_id = node_data.get('parent')
        
        return path
    
    def _deduplicate_matches(self, matches: List[MatchResult]) -> List[MatchResult]:
        """Remove duplicate matches and merge information."""
        node_matches = {}
        
        for match in matches:
            node_id = match.node_id
            
            if node_id in node_matches:
                # Merge with existing match
                existing = node_matches[node_id]
                
                # Take higher confidence score
                existing.confidence_score = max(existing.confidence_score, match.confidence_score)
                
                # Merge sections and terms
                existing.matching_sections.extend(match.matching_sections)
                existing.matching_terms.extend(match.matching_terms)
                
                # Remove duplicates
                existing.matching_sections = list(set(existing.matching_sections))
                existing.matching_terms = list(set(existing.matching_terms))
            else:
                node_matches[node_id] = match
        
        return list(node_matches.values())
    
    def get_leaf_nodes_only(self, matches: List[MatchResult]) -> List[MatchResult]:
        """Filter matches to return only leaf nodes (nodes with templates)."""
        leaf_matches = []
        
        for match in matches:
            node_data = self.ontology[match.node_id]
            children = node_data.get('children', [])
            
            # If node has no children, it's a leaf node
            if not children:
                leaf_matches.append(match)
        
        return leaf_matches
    
    def get_best_match(self, matches: List[MatchResult]) -> Optional[MatchResult]:
        """Get the best matching node with highest confidence."""
        if not matches:
            return None
        
        # Prefer leaf nodes if available
        leaf_matches = self.get_leaf_nodes_only(matches)
        if leaf_matches:
            return leaf_matches[0]  # Already sorted by confidence
        
        # Otherwise return highest confidence match
        return matches[0]
    
    def save_match_results(self, matches: List[MatchResult], output_path: str) -> None:
        """Save match results to JSON file."""
        try:
            results_data = []
            for match in matches:
                results_data.append({
                    'node_id': match.node_id,
                    'label': match.label,
                    'confidence_score': match.confidence_score,
                    'matching_sections': match.matching_sections,
                    'matching_terms': match.matching_terms,
                    'parent_path': match.parent_path
                })
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(results_data, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"Match results saved to {output_path}")
            
        except Exception as e:
            self.logger.error(f"Error saving match results: {e}")
            raise

def main():
    """Example usage of ontology matcher."""
    matcher = OntologyMatcher("ontology_schema.json")
    
    # Example metadata
    sample_metadata = {
        "case_number": "Crl. Appeal No.1192/2011",
        "case_title": "Afsar & Anr. vs. State of Delhi",
        "court_name": "High Court of Delhi",
        "sections_invoked": ["IPC 376", "IPC 363", "POCSO 6"],
        "case_type": "Criminal Appeal"
    }
    
    sample_text = """
    This is a case involving rape and kidnapping. The accused was charged under 
    IPC 376 for rape and IPC 363 for kidnapping. The victim was a minor.
    """
    
    matches = matcher.find_matching_nodes(sample_metadata, sample_text)
    
    print("Matching Results:")
    for match in matches:
        print(f"- {match.label} (ID: {match.node_id})")
        print(f"  Confidence: {match.confidence_score:.2f}")
        print(f"  Sections: {match.matching_sections}")
        print(f"  Terms: {match.matching_terms}")
        print(f"  Path: {' > '.join(match.parent_path)}")
        print()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()