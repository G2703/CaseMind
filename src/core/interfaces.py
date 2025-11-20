"""
Core interfaces and abstract base classes following Interface Segregation Principle.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from pathlib import Path
import numpy as np


class IDocumentLoader(ABC):
    """Interface for document loading operations."""
    
    @abstractmethod
    def load(self, file_path: Path) -> str:
        """Load document and return text content."""
        pass
    
    @abstractmethod
    def validate(self, file_path: Path) -> bool:
        """Validate if file can be loaded."""
        pass


class IMetadataExtractor(ABC):
    """Interface for metadata extraction."""
    
    @abstractmethod
    async def extract(self, text: str, file_path: Optional[Path] = None) -> Dict[str, Any]:
        """Extract metadata from text."""
        pass


class ITemplateSelector(ABC):
    """Interface for template selection."""
    
    @abstractmethod
    def select(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Select appropriate template based on metadata."""
        pass


class IFactExtractor(ABC):
    """Interface for fact extraction."""
    
    @abstractmethod
    async def extract(self, text: str, template: Dict[str, Any]) -> Dict[str, Any]:
        """Extract structured facts based on template."""
        pass


class IEmbedder(ABC):
    """Interface for embedding generation."""
    
    @abstractmethod
    def embed_text(self, text: str) -> np.ndarray:
        """Generate embedding for text."""
        pass
    
    @abstractmethod
    def embed_batch(self, texts: List[str]) -> np.ndarray:
        """Generate embeddings for multiple texts."""
        pass


class IDocumentStore(ABC):
    """Interface for document storage operations."""
    
    @abstractmethod
    def write_document(self, document: Dict[str, Any]) -> str:
        """Store a document and return its ID."""
        pass
    
    @abstractmethod
    def query_by_embedding(
        self, 
        embedding: np.ndarray, 
        top_k: int, 
        embedding_field: str = "embedding_facts"
    ) -> List[Dict[str, Any]]:
        """Query documents by embedding similarity."""
        pass
    
    @abstractmethod
    def get_document_by_id(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve document by ID."""
        pass
    
    @abstractmethod
    def check_duplicate(self, file_hash: str) -> Optional[Dict[str, Any]]:
        """Check if document with given hash exists."""
        pass


class IDuplicateChecker(ABC):
    """Interface for duplicate detection."""
    
    @abstractmethod
    def check(self, file_path: Path, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Check if document is duplicate."""
        pass


class IResultFormatter(ABC):
    """Interface for result formatting and display."""
    
    @abstractmethod
    def format_summary(self, metadata: Dict[str, Any], facts: Dict[str, Any]) -> None:
        """Format and display case summary."""
        pass
    
    @abstractmethod
    def format_similar_cases(self, results: List[Dict[str, Any]]) -> None:
        """Format and display similar cases."""
        pass
    
    @abstractmethod
    def display_progress(self, current: int, total: int, message: str) -> None:
        """Display progress information."""
        pass
