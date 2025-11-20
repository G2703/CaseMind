"""
Utility functions and helper classes.
"""

import hashlib
import logging
from pathlib import Path
from typing import Dict, Any

logger = logging.getLogger(__name__)


def compute_file_hash(file_path: Path) -> str:
    """
    Compute SHA-256 hash of file content.
    
    Args:
        file_path: Path to file
        
    Returns:
        Hexadecimal hash string
    """
    sha256 = hashlib.sha256()
    
    try:
        with open(file_path, 'rb') as f:
            while chunk := f.read(8192):
                sha256.update(chunk)
        return sha256.hexdigest()
    except Exception as e:
        logger.error(f"Failed to compute hash for {file_path}: {e}")
        raise


def generate_case_id(metadata: Dict[str, Any]) -> str:
    """
    Generate unique case ID from metadata.
    
    Args:
        metadata: Case metadata dictionary
        
    Returns:
        Generated case ID
    """
    # Use case title and court as basis for ID
    case_title = metadata.get('case_title', 'unknown')
    court = metadata.get('court_name', 'unknown')
    
    # Create normalized string
    id_string = f"{case_title}_{court}".lower()
    id_string = id_string.replace(' ', '_').replace('vs.', 'vs').replace('.', '')
    
    # Truncate if too long and add hash suffix for uniqueness
    if len(id_string) > 200:
        hash_suffix = hashlib.md5(id_string.encode()).hexdigest()[:8]
        id_string = id_string[:192] + '_' + hash_suffix
    
    return id_string


def construct_metadata_embedding_text(metadata: Dict[str, Any]) -> str:
    """
    Construct searchable text from metadata for embedding.
    Optimized for entity-based retrieval (case names, courts, sections).
    
    Args:
        metadata: Case metadata dictionary
        
    Returns:
        Concatenated metadata text
    """
    parts = []
    
    # Case title and parties
    if 'case_title' in metadata:
        parts.append(f"Case: {metadata['case_title']}")
    
    # Court information
    if 'court_name' in metadata:
        parts.append(f"Court: {metadata['court_name']}")
    
    # Date in natural language
    if 'judgment_date' in metadata:
        parts.append(f"Judgment date: {metadata['judgment_date']}")
    
    # Legal sections
    if 'sections_invoked' in metadata and metadata['sections_invoked']:
        if isinstance(metadata['sections_invoked'], list):
            sections = ', '.join(metadata['sections_invoked'])
        else:
            sections = str(metadata['sections_invoked'])
        parts.append(f"Sections: {sections}")
    
    if 'most_appropriate_section' in metadata:
        parts.append(f"Primary section: {metadata['most_appropriate_section']}")
    
    # Template information
    if 'template_label' in metadata:
        parts.append(f"Case type: {metadata['template_label']}")
    
    # Party information from extracted facts (if available)
    if 'extracted_facts' in metadata:
        facts = metadata['extracted_facts']
        
        # Procedural information
        if 'tier_4_procedural' in facts:
            proc = facts['tier_4_procedural']
            if 'fir_number' in proc and proc['fir_number']:
                parts.append(f"FIR: {proc['fir_number']}")
            if 'police_station' in proc and proc['police_station']:
                parts.append(f"Police station: {proc['police_station']}")
        
        # Party information
        if 'tier_1_parties' in facts:
            parties = facts['tier_1_parties']
            if isinstance(parties, dict):
                if 'appellant' in parties and isinstance(parties['appellant'], dict):
                    if 'name' in parties['appellant'] and parties['appellant']['name']:
                        parts.append(f"Appellant: {parties['appellant']['name']}")
                if 'respondent' in parties and isinstance(parties['respondent'], dict):
                    if 'name' in parties['respondent'] and parties['respondent']['name']:
                        parts.append(f"Respondent: {parties['respondent']['name']}")
                if 'victim' in parties and isinstance(parties['victim'], dict):
                    if 'name' in parties['victim'] and parties['victim']['name']:
                        parts.append(f"Victim: {parties['victim']['name']}")
    
    return ". ".join(parts) + "." if parts else "Unknown case"


def setup_logging(log_level: str = "INFO", disable: bool = False) -> None:
    """
    Setup logging configuration.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        disable: Whether to disable logging
    """
    if disable:
        logging.basicConfig(level=logging.CRITICAL)
        return
    
    # Convert string to logging level
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    
    # Configure logging
    logging.basicConfig(
        level=numeric_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler()
        ]
    )
    
    # Reduce noise from external libraries
    logging.getLogger('sentence_transformers').setLevel(logging.WARNING)
    logging.getLogger('transformers').setLevel(logging.WARNING)
    logging.getLogger('httpx').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)
