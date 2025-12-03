"""
Markdown processing service.
Handles normalization, hashing, compression, and storage.
"""

import hashlib
import re
import logging
from typing import Tuple
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from src.infrastructure.storage_adapter import LocalStorageAdapter

logger = logging.getLogger(__name__)


class MarkdownService:
    """
    Service for markdown file processing.
    Handles normalization, hashing, and storage operations.
    """
    
    def __init__(self, storage_adapter: LocalStorageAdapter):
        """
        Initialize markdown service.
        
        Args:
            storage_adapter: Storage adapter for markdown files
        """
        self.storage = storage_adapter
        logger.info("MarkdownService initialized")
    
    def normalize(self, text: str) -> str:
        """
        Normalize markdown text deterministically.
        
        Normalization ensures same content always produces same hash:
        - Convert line endings to LF
        - Collapse multiple blank lines to single blank line
        - Strip trailing whitespace
        - Ensure single newline at end
        
        Args:
            text: Raw markdown text
            
        Returns:
            Normalized markdown text
        """
        if not text:
            return ""
        
        # Convert all line endings to \n
        text = text.replace('\r\n', '\n').replace('\r', '\n')
        
        # Strip trailing whitespace from each line
        lines = [line.rstrip() for line in text.split('\n')]
        
        # Collapse multiple blank lines to single blank line
        normalized_lines = []
        prev_blank = False
        for line in lines:
            is_blank = len(line.strip()) == 0
            if is_blank and prev_blank:
                continue  # Skip consecutive blank lines
            normalized_lines.append(line)
            prev_blank = is_blank
        
        # Join lines and ensure single newline at end
        normalized = '\n'.join(normalized_lines)
        if normalized and not normalized.endswith('\n'):
            normalized += '\n'
        
        return normalized
    
    def compute_hash(self, markdown: str) -> str:
        """
        Compute SHA-256 hash of markdown text.
        
        Args:
            markdown: Markdown text (should be normalized first)
            
        Returns:
            Hexadecimal SHA-256 hash
        """
        sha256_hash = hashlib.sha256()
        sha256_hash.update(markdown.encode('utf-8'))
        return sha256_hash.hexdigest()
    
    def save(self, markdown: str) -> Tuple[str, str]:
        """
        Normalize, hash, and save markdown to storage.
        
        Args:
            markdown: Raw markdown text
            
        Returns:
            Tuple of (md_hash, storage_uri)
        """
        # Normalize
        normalized = self.normalize(markdown)
        
        # Compute hash
        md_hash = self.compute_hash(normalized)
        
        # Check if already exists
        if self.storage.exists(md_hash):
            logger.debug(f"Markdown already exists in storage: {md_hash}")
            # Reconstruct URI
            from pathlib import Path
            path = self.storage._get_path(md_hash)
            uri = f"file://{path.absolute()}"
            return md_hash, uri
        
        # Upload to storage
        uri = self.storage.upload(md_hash, normalized)
        
        logger.info(f"Saved markdown: {md_hash} -> {uri}")
        
        return md_hash, uri
    
    def load(self, uri: str) -> str:
        """
        Load markdown from storage URI.
        
        Args:
            uri: Storage URI (file://...)
            
        Returns:
            Markdown text
        """
        return self.storage.download(uri)
    
    def exists(self, md_hash: str) -> bool:
        """
        Check if markdown exists in storage.
        
        Args:
            md_hash: SHA-256 hash
            
        Returns:
            True if exists, False otherwise
        """
        return self.storage.exists(md_hash)
