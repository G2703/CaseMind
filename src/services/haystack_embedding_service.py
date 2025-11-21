"""
Haystack-based Embedding Service using SentenceTransformers components.
"""

import logging
import numpy as np
from typing import List, Union
from haystack.components.embedders import SentenceTransformersTextEmbedder, SentenceTransformersDocumentEmbedder
from haystack import Document

from core.config import Config

logger = logging.getLogger(__name__)


class HaystackEmbeddingService:
    """
    Embedding service using Haystack's SentenceTransformers components.
    
    Provides:
    - Text embedding for queries
    - Document embedding for batch processing
    - Consistent interface with old embedding service
    """
    
    def __init__(self):
        """Initialize Haystack embedding components."""
        self.config = Config()
        self.model_name = self.config.get("EMBEDDING_MODEL", "sentence-transformers/all-mpnet-base-v2")
        
        # Initialize Haystack embedders
        self.text_embedder = SentenceTransformersTextEmbedder(
            model=self.model_name,
            progress_bar=False,
            normalize_embeddings=True
        )
        self.text_embedder.warm_up()
        
        self.document_embedder = SentenceTransformersDocumentEmbedder(
            model=self.model_name,
            progress_bar=False,
            normalize_embeddings=True
        )
        self.document_embedder.warm_up()
        
        logger.info(f"Haystack Embedding Service initialized with model: {self.model_name}")
    
    def embed_text(self, text: str) -> np.ndarray:
        """
        Embed single text query.
        
        Args:
            text: Text to embed
            
        Returns:
            numpy array of embedding (768-dim)
        """
        result = self.text_embedder.run(text=text)
        embedding_list = result['embedding']
        return np.array(embedding_list, dtype=np.float32)
    
    def embed_texts(self, texts: List[str]) -> List[np.ndarray]:
        """
        Embed multiple texts.
        
        Args:
            texts: List of texts to embed
            
        Returns:
            List of numpy arrays
        """
        embeddings = []
        for text in texts:
            embeddings.append(self.embed_text(text))
        return embeddings
    
    def embed_documents(self, documents: List[Document]) -> List[Document]:
        """
        Embed Haystack Documents in place.
        
        Args:
            documents: List of Haystack Documents
            
        Returns:
            Documents with embeddings added
        """
        result = self.document_embedder.run(documents=documents)
        return result['documents']
    
    def get_embedding_dimension(self) -> int:
        """Get embedding dimension."""
        return 768  # all-mpnet-base-v2 produces 768-dim vectors


# Backward compatibility alias
EmbeddingService = HaystackEmbeddingService
