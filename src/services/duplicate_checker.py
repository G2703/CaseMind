"""
Duplicate detection service using file hashing and metadata matching.
Implements IDuplicateChecker interface.
"""

import logging
from typing import Dict, Any, Optional
from pathlib import Path

from core.interfaces import IDuplicateChecker, IDocumentStore
from core.models import DuplicateStatus, MatchMethod
from utils.helpers import compute_file_hash

logger = logging.getLogger(__name__)


class DuplicateChecker(IDuplicateChecker):
    """
    Check for duplicate documents using multiple strategies:
    1. File hash (most reliable)
    2. Case ID matching
    3. Fuzzy title matching (future enhancement)
    """
    
    def __init__(self, document_store: IDocumentStore):
        """
        Initialize duplicate checker.
        
        Args:
            document_store: Document store for querying existing documents
        """
        self.store = document_store
        logger.info("Duplicate checker initialized")
    
    def check(
        self, 
        file_path: Path, 
        metadata: Optional[Dict[str, Any]] = None
    ) -> DuplicateStatus:
        """
        Check if document is a duplicate.
        
        Args:
            file_path: Path to document file
            metadata: Optional metadata for additional checks
            
        Returns:
            DuplicateStatus object with detection results
        """
        try:
            # Strategy 1: File hash check (most reliable)
            file_hash = compute_file_hash(file_path)
            hash_result = self.store.check_duplicate(file_hash)
            
            if hash_result:
                logger.info(f"Duplicate detected by file hash: {hash_result.get('case_id')}")
                return DuplicateStatus(
                    is_duplicate=True,
                    existing_case_id=hash_result.get('case_id'),
                    match_method=MatchMethod.FILE_HASH,
                    similarity_score=1.0
                )
            
            # Strategy 2: Case ID check (if metadata available)
            if metadata and 'case_id' in metadata:
                case_id = metadata['case_id']
                case_result = self.store.get_document_by_id(case_id)
                
                if case_result:
                    logger.info(f"Duplicate detected by case ID: {case_id}")
                    return DuplicateStatus(
                        is_duplicate=True,
                        existing_case_id=case_id,
                        match_method=MatchMethod.CASE_ID,
                        similarity_score=0.95
                    )
            
            # Strategy 3: Fuzzy title matching (future enhancement)
            # Could use Levenshtein distance or embedding similarity
            # if metadata and 'case_title' in metadata:
            #     Similar case detection based on title
            #     pass
            
            # No duplicate found
            logger.debug(f"No duplicate found for: {file_path.name}")
            return DuplicateStatus(
                is_duplicate=False,
                existing_case_id=None,
                match_method=MatchMethod.NEW,
                similarity_score=0.0
            )
            
        except Exception as e:
            logger.error(f"Error during duplicate check: {e}")
            # On error, assume not duplicate to allow processing
            return DuplicateStatus(
                is_duplicate=False,
                existing_case_id=None,
                match_method=MatchMethod.NEW,
                similarity_score=0.0
            )
