"""
Text chunking service using Haystack's RecursiveDocumentSplitter.
Implements semantic chunking with paragraph and sentence separators.
"""

import logging
from typing import List
from haystack.components.preprocessors import RecursiveDocumentSplitter
from haystack.dataclasses import Document as HaystackDocument
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
    Service for semantic text chunking using Haystack's RecursiveDocumentSplitter.
    Splits text at natural boundaries (paragraphs, sentences) for legal documents.
    """
    
    def __init__(self, chunk_size: int = None, overlap: int = None):
        """
        Initialize chunking service with RecursiveDocumentSplitter.
        
        Args:
            chunk_size: Number of tokens per chunk (default from config)
            overlap: Number of tokens to overlap (default from config)
        """
        config = Config()
        self.chunk_size = chunk_size or config.chunk_size_tokens
        self.overlap = overlap or config.chunk_overlap_tokens
        
        # Initialize Haystack's RecursiveDocumentSplitter with paragraph separators
        # Separators are applied in order: double newline (paragraphs) -> sentences -> single newline -> space
        self.splitter = RecursiveDocumentSplitter(
            split_length=self.chunk_size,
            split_overlap=self.overlap,
            split_unit="token",
            separators=["\n\n", "sentence", "\n", " "],
            sentence_splitter_params={
                "language": "en",
                "use_split_rules": True,
                "keep_white_spaces": False
            }
        )
        
        # Initialize tokenizer for token counting
        embedding_model_name = config.embedding_model
        logger.info(f"Loading tokenizer from {embedding_model_name}")
        self.model = SentenceTransformer(embedding_model_name)
        self.tokenizer = self.model.tokenizer
        
        # Warm up the splitter
        self.splitter.warm_up()
        
        logger.info(
            f"ChunkingService initialized with RecursiveDocumentSplitter "
            f"(chunk_size={self.chunk_size} tokens, overlap={self.overlap} tokens, "
            f"separators=['\\n\\n', 'sentence', '\\n', ' '])"
        )
    
    def chunk_text(self, text: str) -> List[TextChunk]:
        """
        Split text into overlapping chunks using recursive separator-based splitting.
        
        Args:
            text: Input text to chunk
            
        Returns:
            List of TextChunk objects
        """
        if not text or not text.strip():
            logger.warning("Empty text provided for chunking")
            return []
        
        # Create Haystack document
        haystack_doc = HaystackDocument(content=text)
        
        # Split using RecursiveDocumentSplitter
        result = self.splitter.run(documents=[haystack_doc])
        split_documents = result.get("documents", [])
        
        if not split_documents:
            logger.warning("No chunks created from text")
            return []
        
        # Convert Haystack documents to TextChunk objects
        chunks = []
        for idx, doc in enumerate(split_documents):
            chunk_text = doc.content
            token_count = self.get_token_count(chunk_text)
            
            chunk = TextChunk(
                chunk_index=idx,
                text=chunk_text,
                token_count=token_count
            )
            chunks.append(chunk)
            logger.debug(f"Created chunk {idx}: {token_count} tokens")
        
        total_tokens = sum(c.token_count for c in chunks)
        logger.info(
            f"Created {len(chunks)} chunks from {total_tokens} total tokens "
            f"(avg {total_tokens // len(chunks)} tokens/chunk)"
        )
        
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
