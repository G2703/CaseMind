"""
Embedding service.
Handles batch embedding generation and L2 normalization.
"""

import logging
from typing import List
import numpy as np
from sentence_transformers import SentenceTransformer
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from src.core.config import Config

logger = logging.getLogger(__name__)


class EmbeddingService:
    """
    Service for generating embeddings using SentenceTransformers.
    Handles batch processing and L2 normalization for cosine similarity.
    """
    
    def __init__(self, model_name: str = None):
        """
        Initialize embedding service.
        
        Args:
            model_name: Model name for embeddings (default from config)
        """
        config = Config()
        self.model_name = model_name or config.embedding_model
        
        logger.info(f"Loading embedding model: {self.model_name}")
        self.model = SentenceTransformer(self.model_name)
        
        logger.info(f"EmbeddingService initialized with {self.model_name}")
    
    def embed_batch(self, texts: List[str], normalize: bool = True) -> List[List[float]]:
        """
        Generate embeddings for batch of texts.
        
        Args:
            texts: List of text strings to embed
            normalize: Whether to L2-normalize vectors (default True for cosine similarity)
            
        Returns:
            List of embedding vectors (as lists of floats)
        """
        if not texts:
            logger.warning("Empty text list provided for embedding")
            return []
        
        # Filter out empty texts
        valid_texts = [text if text and text.strip() else "empty" for text in texts]
        
        logger.debug(f"Encoding {len(valid_texts)} texts")
        
        try:
            # Generate embeddings
            embeddings = self.model.encode(
                valid_texts,
                batch_size=32,
                show_progress_bar=False,
                convert_to_numpy=True
            )
            
            # L2 normalize if requested (for cosine similarity)
            if normalize:
                embeddings = self._normalize_l2(embeddings)
            
            # Convert to list of lists
            embeddings_list = embeddings.tolist()
            
            logger.debug(f"Generated {len(embeddings_list)} embeddings of dimension {len(embeddings_list[0])}")
            
            return embeddings_list
            
        except Exception as e:
            logger.error(f"Embedding generation failed: {e}")
            # Return zero vectors as fallback
            dim = 768  # all-mpnet-base-v2 dimension
            return [[0.0] * dim for _ in range(len(texts))]
    
    def embed_single(self, text: str, normalize: bool = True) -> List[float]:
        """
        Generate embedding for single text.
        
        Args:
            text: Text string to embed
            normalize: Whether to L2-normalize vector
            
        Returns:
            Embedding vector as list of floats
        """
        embeddings = self.embed_batch([text], normalize=normalize)
        return embeddings[0] if embeddings else [0.0] * 768
    
    def _normalize_l2(self, vectors: np.ndarray) -> np.ndarray:
        """
        L2 normalize vectors for cosine similarity.
        
        Args:
            vectors: Numpy array of shape (n, d)
            
        Returns:
            L2-normalized vectors
        """
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        # Avoid division by zero
        norms = np.where(norms == 0, 1, norms)
        return vectors / norms
    
    def get_embedding_dimension(self) -> int:
        """
        Get the dimension of embeddings produced by this model.
        
        Returns:
            Embedding dimension
        """
        return self.model.get_sentence_embedding_dimension()
