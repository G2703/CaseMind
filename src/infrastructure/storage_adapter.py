"""
Local storage adapter for markdown files.
Implements content-addressed storage for canonical markdown.
"""

from pathlib import Path
import gzip
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class LocalStorageAdapter:
    """
    Local filesystem storage for markdown files.
    Uses content-addressed paths for deduplication.
    """
    
    def __init__(self, base_path: Path):
        """
        Initialize local storage adapter.
        
        Args:
            base_path: Base directory for storage (e.g., 'cases/local_storage_md')
        """
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"LocalStorageAdapter initialized at: {self.base_path}")
    
    def _get_path(self, md_hash: str) -> Path:
        """
        Get content-addressed path for md_hash.
        
        Path structure: base_path/ab/cd/abcd1234...md.gz
        
        Args:
            md_hash: SHA256 hash of markdown
            
        Returns:
            Path object for the file
        """
        if len(md_hash) < 4:
            raise ValueError(f"md_hash too short: {md_hash}")
        
        # Create nested directories from first 4 chars of hash
        return self.base_path / md_hash[:2] / md_hash[2:4] / f"{md_hash}.md.gz"
    
    def upload(self, md_hash: str, content: str) -> str:
        """
        Upload compressed markdown to storage.
        
        Args:
            md_hash: SHA256 hash of markdown
            content: Markdown text content
            
        Returns:
            Local URI (file://path/to/file)
        """
        try:
            path = self._get_path(md_hash)
            path.parent.mkdir(parents=True, exist_ok=True)
            
            # Compress with gzip
            compressed = gzip.compress(content.encode('utf-8'))
            path.write_bytes(compressed)
            
            uri = f"file://{path.absolute()}"
            logger.debug(f"Uploaded markdown: {uri} ({len(content)} chars, {len(compressed)} bytes compressed)")
            
            return uri
            
        except Exception as e:
            logger.error(f"Failed to upload markdown for hash {md_hash}: {e}")
            raise
    
    def download(self, uri: str) -> str:
        """
        Download and decompress markdown from storage.
        
        Args:
            uri: Local file URI (file://path)
            
        Returns:
            Decompressed markdown text
        """
        try:
            # Remove file:// prefix
            path = Path(uri.replace('file://', ''))
            
            if not path.exists():
                raise FileNotFoundError(f"Markdown file not found: {path}")
            
            # Decompress
            compressed = path.read_bytes()
            markdown = gzip.decompress(compressed).decode('utf-8')
            
            logger.debug(f"Downloaded markdown from {uri} ({len(markdown)} chars)")
            
            return markdown
            
        except Exception as e:
            logger.error(f"Failed to download markdown from {uri}: {e}")
            raise
    
    def exists(self, md_hash: str) -> bool:
        """
        Check if markdown file exists in storage.
        
        Args:
            md_hash: SHA256 hash of markdown
            
        Returns:
            True if file exists, False otherwise
        """
        path = self._get_path(md_hash)
        return path.exists()
    
    def delete(self, md_hash: str) -> bool:
        """
        Delete markdown file from storage.
        
        Args:
            md_hash: SHA256 hash of markdown
            
        Returns:
            True if deleted, False if file didn't exist
        """
        try:
            path = self._get_path(md_hash)
            
            if not path.exists():
                logger.warning(f"Cannot delete, file not found: {md_hash}")
                return False
            
            path.unlink()
            logger.debug(f"Deleted markdown file: {md_hash}")
            
            # Clean up empty directories
            try:
                path.parent.rmdir()  # Remove ab/cd/
                path.parent.parent.rmdir()  # Remove ab/
            except OSError:
                pass  # Directories not empty, that's fine
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete markdown {md_hash}: {e}")
            return False
    
    def get_stats(self) -> dict:
        """
        Get storage statistics.
        
        Returns:
            Dictionary with file count and total size
        """
        total_files = 0
        total_bytes = 0
        
        for path in self.base_path.rglob("*.md.gz"):
            total_files += 1
            total_bytes += path.stat().st_size
        
        return {
            "total_files": total_files,
            "total_bytes": total_bytes,
            "total_mb": round(total_bytes / (1024 * 1024), 2),
            "base_path": str(self.base_path),
        }
