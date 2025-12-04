"""
Stage 2: Markdown Normalizer & Storage
Haystack component for markdown normalization, hashing, and content-addressed storage.
"""

from typing import List, Dict, Any
from pathlib import Path
import logging
import uuid
import hashlib
import sys
import os

from haystack import component, Document

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from src.core.config import Config

logger = logging.getLogger(__name__)


@component
class MarkdownNormalizer:
    """
    Haystack component for markdown normalization and storage.
    
    Inputs:
        - documents (List[Document]): Haystack documents with markdown content
    
    Outputs:
        - documents (List[Document]): Documents with md_hash, md_uri, file_id added to meta
    """
    
    # Namespace for deterministic UUID generation
    NAMESPACE = uuid.UUID('6ba7b810-9dad-11d1-80b4-00c04fd430c8')
    
    def __init__(self):
        """Initialize markdown normalizer."""
        config = Config()
        self.storage_path = Path(config.local_storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"MarkdownNormalizer initialized with storage: {self.storage_path}")
    
    def _normalize(self, text: str) -> str:
        """Normalize markdown text deterministically."""
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
                continue
            normalized_lines.append(line)
            prev_blank = is_blank
        
        # Join lines and ensure single newline at end
        normalized = '\n'.join(normalized_lines)
        if normalized and not normalized.endswith('\n'):
            normalized += '\n'
        
        return normalized
    
    def _compute_hash(self, markdown: str) -> str:
        """Compute SHA-256 hash of markdown text."""
        sha256_hash = hashlib.sha256()
        sha256_hash.update(markdown.encode('utf-8'))
        return sha256_hash.hexdigest()
    
    def _save_markdown(self, markdown: str) -> tuple[str, str]:
        """Save markdown to content-addressed storage."""
        # Normalize
        normalized = self._normalize(markdown)
        
        # Compute hash
        md_hash = self._compute_hash(normalized)
        
        # Create filename from hash
        file_path = self.storage_path / f"{md_hash}.md"
        
        # Check if already exists
        if file_path.exists():
            logger.debug(f"Markdown already exists in storage: {md_hash}")
        else:
            # Write to file
            file_path.write_text(normalized, encoding='utf-8')
            logger.info(f"Saved markdown: {md_hash}")
        
        # Create URI
        uri = f"file://{file_path.absolute()}"
        
        return md_hash, uri
    
    @component.output_types(documents=List[Document])
    def run(self, documents: List[Document]) -> Dict[str, Any]:
        """
        Normalize, hash, and store markdown.
        
        Args:
            documents: List of Haystack documents with markdown content
            
        Returns:
            Dictionary with 'documents' key containing List[Document] with updated metadata
        """
        processed_docs = []
        
        for doc in documents:
            # Skip error documents
            if "error" in doc.meta:
                processed_docs.append(doc)
                continue
            
            try:
                # Normalize, hash, and save markdown
                md_hash, md_uri = self._save_markdown(doc.content)
                
                # Generate deterministic file_id from md_hash
                file_id = str(uuid.uuid5(self.NAMESPACE, md_hash))
                
                # Update document metadata
                doc.meta.update({
                    "md_hash": md_hash,
                    "md_uri": md_uri,
                    "file_id": file_id
                })
                
                logger.info(f"✓ Normalized {doc.meta['original_filename']}: hash={md_hash[:8]}..., file_id={file_id}")
                processed_docs.append(doc)
                
            except Exception as e:
                logger.error(f"Failed to normalize {doc.meta.get('original_filename', 'unknown')}: {e}")
                doc.meta["error"] = str(e)
                processed_docs.append(doc)
        
        return {"documents": processed_docs}
