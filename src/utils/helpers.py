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
