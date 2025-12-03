"""
Text chunking service.
Handles tokenization and chunking with overlap for embedding.
"""

import logging
from typing import List
from sentence_transformers import SentenceTransformer
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from src.core.config import Config
from src.core.models import TextChunk

logger = logging.getLogger(__name__)


class ChunkingService:
    """
    Service for text chunking with token-based splitting.
    Uses embedding model's tokenizer for accurate token counting.
    """
    
    def __init__(self, chunk_size: int = None, overlap: int = None):
        """
        Initialize chunking service.
        
        Args:
            chunk_size: Number of tokens per chunk (default from config)
            overlap: Number of tokens to overlap (default from config)
        """
        config = Config()
        self.chunk_size = chunk_size or config.chunk_size_tokens
        self.overlap = overlap or config.chunk_overlap_tokens
        
        # Initialize tokenizer from embedding model
        embedding_model_name = config.embedding_model
        logger.info(f"Loading tokenizer from {embedding_model_name}")
        self.model = SentenceTransformer(embedding_model_name)
        self.tokenizer = self.model.tokenizer
        
        logger.info(f"ChunkingService initialized (chunk_size={self.chunk_size}, overlap={self.overlap})")
    
    def chunk_text(self, text: str) -> List[TextChunk]:
        """
        Split text into overlapping chunks based on token count.
        
        Args:
            text: Input text to chunk
            
        Returns:
            List of TextChunk objects
        """
        if not text or not text.strip():
            logger.warning("Empty text provided for chunking")
            return []
        
        # Tokenize the entire text
        tokens = self.tokenizer.tokenize(text)
        total_tokens = len(tokens)
        
        if total_tokens == 0:
            logger.warning("Text tokenized to zero tokens")
            return []
        
        logger.debug(f"Text tokenized to {total_tokens} tokens")
        
        chunks = []
        chunk_index = 0
        start_idx = 0
        
        while start_idx < total_tokens:
            # Calculate end index for this chunk
            end_idx = min(start_idx + self.chunk_size, total_tokens)
            
            # Extract chunk tokens
            chunk_tokens = tokens[start_idx:end_idx]
            
            # Convert tokens back to text
            chunk_text = self.tokenizer.convert_tokens_to_string(chunk_tokens)
            
            # Create TextChunk object
            chunk = TextChunk(
                chunk_index=chunk_index,
                text=chunk_text,
                token_count=len(chunk_tokens)
            )
            
            chunks.append(chunk)
            
            logger.debug(f"Created chunk {chunk_index}: {len(chunk_tokens)} tokens")
            
            # Move start index forward (with overlap)
            chunk_index += 1
            start_idx += (self.chunk_size - self.overlap)
        
        logger.info(f"Created {len(chunks)} chunks from {total_tokens} tokens")
        
        return chunks
    
    def get_token_count(self, text: str) -> int:
        """
        Get token count for text.
        
        Args:
            text: Input text
            
        Returns:
            Number of tokens
        """
        if not text:
            return 0
        
        tokens = self.tokenizer.tokenize(text)
        return len(tokens)
