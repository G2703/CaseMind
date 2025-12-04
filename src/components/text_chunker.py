"""
Stage 3: Text Chunker
Haystack component for semantic text chunking with overlap.
"""

from typing import List, Dict, Any
import logging
import sys
import os

from haystack import component, Document
from haystack.components.preprocessors import RecursiveDocumentSplitter
from haystack.dataclasses import Document as HaystackDocument
from sentence_transformers import SentenceTransformer

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from src.core.config import Config

logger = logging.getLogger(__name__)


@component
class TextChunker:
    """
    Haystack component for text chunking using RecursiveDocumentSplitter.
    
    Inputs:
        - documents (List[Document]): Haystack documents with markdown content
    
    Outputs:
        - documents (List[Document]): Original documents (unchanged)
        - chunks (List[Dict]): Text chunks with metadata (chunk_index, text, token_count, file_id)
    """
    
    def __init__(self, chunk_size: int = None, overlap: int = None):
        """
        Initialize text chunker.
        
        Args:
            chunk_size: Number of tokens per chunk (default from config)
            overlap: Number of tokens to overlap (default from config)
        """
        config = Config()
        self.chunk_size = chunk_size or config.chunk_size_tokens
        self.overlap = overlap or config.chunk_overlap_tokens
        
        # Initialize Haystack's RecursiveDocumentSplitter
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
            f"TextChunker initialized with RecursiveDocumentSplitter "
            f"(chunk_size={self.chunk_size} tokens, overlap={self.overlap} tokens)"
        )
    
    def _get_token_count(self, text: str) -> int:
        """Get token count for text."""
        if not text:
            return 0
        tokens = self.tokenizer.tokenize(text)
        return len(tokens)
    
    def _chunk_text(self, text: str) -> List[Dict[str, Any]]:
        """Split text into overlapping chunks."""
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
        
        # Convert to dictionaries
        chunks = []
        for idx, doc in enumerate(split_documents):
            chunk_text = doc.content
            token_count = self._get_token_count(chunk_text)
            
            chunk = {
                "chunk_index": idx,
                "text": chunk_text,
                "token_count": token_count
            }
            chunks.append(chunk)
        
        total_tokens = sum(c["token_count"] for c in chunks)
        logger.debug(
            f"Created {len(chunks)} chunks from {total_tokens} total tokens "
            f"(avg {total_tokens // len(chunks)} tokens/chunk)"
        )
        
        return chunks
    
    @component.output_types(documents=List[Document], chunks=List[Dict[str, Any]])
    def run(self, documents: List[Document]) -> Dict[str, Any]:
        """
        Chunk text into overlapping segments.
        
        Args:
            documents: List of Haystack documents
            
        Returns:
            Dictionary with 'documents' and 'chunks' keys
        """
        all_chunks = []
        
        for doc in documents:
            # Skip error documents
            if "error" in doc.meta:
                continue
            
            try:
                # Chunk text
                chunks = self._chunk_text(doc.content)
                
                # Add file_id to each chunk
                file_id = doc.meta.get("file_id", "")
                for chunk in chunks:
                    chunk["file_id"] = file_id
                    all_chunks.append(chunk)
                
                logger.info(f"✓ Chunked {doc.meta['original_filename']}: {len(chunks)} chunks")
                
            except Exception as e:
                logger.error(f"Failed to chunk {doc.meta.get('original_filename', 'unknown')}: {e}")
        
        logger.info(f"Total chunks created: {len(all_chunks)}")
        return {
            "documents": documents,
            "chunks": all_chunks
        }
