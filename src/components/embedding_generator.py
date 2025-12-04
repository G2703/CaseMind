"""
Stage 5: Embedding Generator
Haystack component for batch embedding generation with L2 normalization.
"""

from typing import List, Dict, Any
import logging
import numpy as np

from haystack import component, Document
from sentence_transformers import SentenceTransformer

import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from src.core.config import Config

logger = logging.getLogger(__name__)


@component
class EmbeddingGenerator:
    """
    Haystack component for generating embeddings for sections and chunks.
    
    Inputs:
        - documents (List[Document]): Documents (passed through)
        - chunks (List[Dict]): Text chunks
        - extractions (List[Dict]): Extractions (passed through)
        - sections (List[Dict]): Case sections
    
    Outputs:
        - documents (List[Document]): Documents (passed through unchanged)
        - chunks (List[Dict]): Chunks with embeddings added
        - extractions (List[Dict]): Extractions (passed through unchanged)
        - sections (List[Dict]): Sections with embeddings added
    """
    
    def __init__(self, model_name: str = None):
        """
        Initialize embedding generator.
        
        Args:
            model_name: Model name for embeddings (default from config)
        """
        config = Config()
        self.model_name = model_name or config.embedding_model
        
        logger.info(f"Loading embedding model: {self.model_name}")
        self.model = SentenceTransformer(self.model_name)
        
        logger.info(f"EmbeddingGenerator initialized with {self.model_name}")
    
    def _normalize_l2(self, vectors: np.ndarray) -> np.ndarray:
        """L2 normalize vectors for cosine similarity."""
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        # Avoid division by zero
        norms = np.where(norms == 0, 1, norms)
        return vectors / norms
    
    def _embed_batch(self, texts: List[str], normalize: bool = True) -> List[List[float]]:
        """Generate embeddings for batch of texts."""
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
            
            # L2 normalize if requested
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
    
    @component.output_types(
        documents=List[Document],
        chunks=List[Dict[str, Any]],
        extractions=List[Dict[str, Any]],
        sections=List[Dict[str, Any]]
    )
    def run(
        self,
        documents: List[Document],
        chunks: List[Dict[str, Any]],
        extractions: List[Dict[str, Any]],
        sections: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Generate embeddings for sections and chunks.
        
        Args:
            documents: Haystack documents (passed through)
            chunks: Text chunks
            extractions: Comprehensive extractions (passed through)
            sections: Case sections
            
        Returns:
            Dictionary with all inputs plus embeddings added
        """
        try:
            # Generate embeddings for sections
            if sections:
                section_texts = [s["text"] for s in sections]
                section_embeddings = self._embed_batch(section_texts, normalize=True)
                
                # Add embeddings to sections
                for section, embedding in zip(sections, section_embeddings):
                    section["vector"] = embedding
                
                logger.info(f"✓ Generated embeddings for {len(sections)} sections")
            
            # Generate embeddings for chunks
            if chunks:
                chunk_texts = [c["text"] for c in chunks]
                chunk_embeddings = self._embed_batch(chunk_texts, normalize=True)
                
                # Add embeddings to chunks
                for chunk, embedding in zip(chunks, chunk_embeddings):
                    chunk["vector"] = embedding
                
                logger.info(f"✓ Generated embeddings for {len(chunks)} chunks")
            
        except Exception as e:
            logger.error(f"Failed to generate embeddings: {e}")
            # Mark documents with error
            for doc in documents:
                if "error" not in doc.meta:
                    doc.meta["error"] = str(e)
                    doc.meta["error_stage"] = "embedding_generator"
        
        return {
            "documents": documents,
            "chunks": chunks,
            "extractions": extractions,
            "sections": sections
        }
