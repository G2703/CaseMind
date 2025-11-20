"""
Embedding service using Sentence Transformers.
Implements dual embedding generation (facts + metadata).
"""

import logging
from typing import List, Dict, Any
import numpy as np
from sentence_transformers import SentenceTransformer

from core.interfaces import IEmbedder
from core.exceptions import EmbeddingError
from core.config import Config
from utils.helpers import construct_metadata_embedding_text

logger = logging.getLogger(__name__)


class EmbeddingService(IEmbedder):
    """
    Embedding service using Sentence Transformers.
    Supports dual embeddings: facts and metadata.
    """
    
    def __init__(self, model_name: str = None):
        """
        Initialize embedding service.
        
        Args:
            model_name: Name of sentence-transformers model
        """
        self.config = Config()
        self.model_name = model_name or self.config.embedding_model
        
        try:
            self.model = SentenceTransformer(self.model_name)
            logger.info(f"Loaded embedding model: {self.model_name}")
        except Exception as e:
            logger.error(f"Failed to load embedding model: {e}")
            raise EmbeddingError(f"Model loading failed: {e}")
    
    def embed_text(self, text: str) -> np.ndarray:
        """
        Generate embedding for single text.
        
        Args:
            text: Input text
            
        Returns:
            Embedding vector as numpy array
        """
        try:
            embedding = self.model.encode(text, convert_to_numpy=True)
            return embedding
        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            raise EmbeddingError(f"Embedding generation failed: {e}")
    
    def embed_batch(self, texts: List[str]) -> np.ndarray:
        """
        Generate embeddings for multiple texts.
        
        Args:
            texts: List of input texts
            
        Returns:
            Array of embeddings
        """
        try:
            embeddings = self.model.encode(texts, convert_to_numpy=True, show_progress_bar=False)
            return embeddings
        except Exception as e:
            logger.error(f"Failed to generate batch embeddings: {e}")
            raise EmbeddingError(f"Batch embedding generation failed: {e}")
    
    def embed_facts(self, facts_text: str) -> np.ndarray:
        """
        Generate embedding for case facts.
        
        Args:
            facts_text: Facts summary text
            
        Returns:
            Facts embedding vector
        """
        return self.embed_text(facts_text)
    
    def embed_metadata(self, metadata: Dict[str, Any]) -> np.ndarray:
        """
        Generate embedding for case metadata.
        
        Args:
            metadata: Case metadata dictionary
            
        Returns:
            Metadata embedding vector
        """
        # Construct metadata text optimized for entity search
        metadata_text = construct_metadata_embedding_text(metadata)
        return self.embed_text(metadata_text)
    
    def embed_document_dual(
        self, 
        facts_text: str, 
        metadata: Dict[str, Any]
    ) -> Dict[str, np.ndarray]:
        """
        Generate both facts and metadata embeddings.
        
        Args:
            facts_text: Facts summary text
            metadata: Case metadata
            
        Returns:
            Dictionary with both embeddings
        """
        return {
            'embedding_facts': self.embed_facts(facts_text),
            'embedding_metadata': self.embed_metadata(metadata)
        }

    def embed_query(self, text: str) -> np.ndarray:
        """
        Compatibility wrapper used by validation and query code.

        Args:
            text: Input query text

        Returns:
            Embedding vector as numpy array
        """
        return self.embed_text(text)
