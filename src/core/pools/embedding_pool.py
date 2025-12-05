"""
Embedding model pool (singleton pattern).
Pre-loads embedding model and provides thread-safe access.
"""

import asyncio
import logging
from typing import Optional, List
import numpy as np

from sentence_transformers import SentenceTransformer
from src.core.config import Config

logger = logging.getLogger(__name__)


class EmbeddingModelPool:
    """
    Singleton pool for embedding model.
    Loads model once, provides thread-safe batched inference.
    """
    
    _instance: Optional['EmbeddingModelPool'] = None
    _lock = asyncio.Lock()
    
    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self, model_name: Optional[str] = None, config: Optional[Config] = None):
        """
        Initialize embedding model pool.
        
        Args:
            model_name: Model name (defaults to config.embedding_model)
            config: Configuration instance
        """
        # Only initialize once
        if hasattr(self, '_initialized') and self._initialized:
            return
        
        self.config = config or Config()
        self.model_name = model_name or self.config.embedding_model
        self.model: Optional[SentenceTransformer] = None
        self._initialized = False
        self.inference_lock = asyncio.Lock()
        
        logger.info(f"EmbeddingModelPool created for {self.model_name}")
    
    async def initialize(self) -> None:
        """Load the embedding model."""
        if self._initialized:
            logger.warning("EmbeddingModelPool already initialized")
            return
        
        logger.info(f"Loading embedding model: {self.model_name}...")
        
        try:
            # Load model in executor to avoid blocking
            loop = asyncio.get_event_loop()
            self.model = await loop.run_in_executor(
                None,
                self._load_model
            )
            
            self._initialized = True
            logger.info(f"✓ Embedding model loaded: {self.model_name}")
            
            # Warm up with dummy inference
            await self._warmup()
            
        except Exception as e:
            logger.error(f"Failed to load embedding model: {e}")
            raise
    
    def _load_model(self) -> SentenceTransformer:
        """Load model (runs in executor)."""
        return SentenceTransformer(self.model_name)
    
    async def _warmup(self) -> None:
        """Warm up model with dummy inference."""
        logger.info("Warming up embedding model...")
        try:
            await self.encode_batch(["warmup text"], normalize=True)
            logger.info("✓ Model warmup complete")
        except Exception as e:
            logger.warning(f"Model warmup failed: {e}")
    
    def _normalize_l2(self, vectors: np.ndarray) -> np.ndarray:
        """L2 normalize vectors."""
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        norms = np.where(norms == 0, 1, norms)
        return vectors / norms
    
    async def encode_batch(
        self,
        texts: List[str],
        normalize: bool = True,
        batch_size: int = 32
    ) -> List[List[float]]:
        """
        Encode batch of texts to embeddings.
        Thread-safe batched inference.
        
        Args:
            texts: List of texts to encode
            normalize: L2 normalize embeddings
            batch_size: Batch size for encoding
            
        Returns:
            List of embedding vectors
        """
        if not self._initialized:
            raise RuntimeError("Model not initialized. Call initialize() first.")
        
        if not texts:
            return []
        
        # Filter empty texts
        valid_texts = [text if text and text.strip() else "empty" for text in texts]
        
        # Thread-safe inference
        async with self.inference_lock:
            logger.debug(f"Encoding {len(valid_texts)} texts...")
            
            try:
                # Run encoding in executor to avoid blocking
                loop = asyncio.get_event_loop()
                embeddings = await loop.run_in_executor(
                    None,
                    self._encode_sync,
                    valid_texts,
                    normalize,
                    batch_size
                )
                
                logger.debug(f"✓ Encoded {len(embeddings)} embeddings")
                return embeddings
                
            except Exception as e:
                logger.error(f"Embedding generation failed: {e}")
                # Return zero vectors as fallback
                dim = 768  # all-mpnet-base-v2 dimension
                return [[0.0] * dim for _ in range(len(texts))]
    
    def _encode_sync(
        self,
        texts: List[str],
        normalize: bool,
        batch_size: int
    ) -> List[List[float]]:
        """Synchronous encoding (runs in executor)."""
        embeddings = self.model.encode(
            texts,
            batch_size=batch_size,
            show_progress_bar=False,
            convert_to_numpy=True
        )
        
        if normalize:
            embeddings = self._normalize_l2(embeddings)
        
        return embeddings.tolist()
    
    async def close(self) -> None:
        """Cleanup resources."""
        logger.info("Closing EmbeddingModelPool...")
        self.model = None
        self._initialized = False
        logger.info("✓ EmbeddingModelPool closed")
    
    def get_status(self) -> dict:
        """Get pool status."""
        return {
            "model_name": self.model_name,
            "initialized": self._initialized,
            "model_loaded": self.model is not None
        }
