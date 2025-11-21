"""
Haystack Document Converter for CaseMind.
Converts between custom data models and Haystack Document objects.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from haystack import Document

logger = logging.getLogger(__name__)


class HaystackDocumentConverter:
    """
    Converts between CaseMind's custom data structures and Haystack Document objects.
    
    Haystack Documents have:
    - id: str (unique identifier)
    - content: str (main text content)
    - meta: Dict[str, Any] (all metadata)
    - embedding: Optional[List[float]] (single embedding vector)
    
    CaseMind uses dual embeddings (facts + metadata), so we store both in meta.
    """
    
    @staticmethod
    def to_haystack_document(
        doc_id: str,
        content: str,
        metadata: Dict[str, Any],
        embedding_facts: Optional[List[float]] = None,
        embedding_metadata: Optional[List[float]] = None,
        file_hash: Optional[str] = None,
        original_filename: Optional[str] = None
    ) -> Document:
        """
        Convert CaseMind data to Haystack Document.
        
        Args:
            doc_id: Unique document identifier (case_id)
            content: Main text content (facts summary or full text)
            metadata: Case metadata dict
            embedding_facts: Facts embedding vector
            embedding_metadata: Metadata embedding vector
            file_hash: Hash of original PDF file
            original_filename: Original PDF filename
            
        Returns:
            Haystack Document object
        """
        # Build comprehensive metadata
        meta = {
            **metadata,
            'file_hash': file_hash,
            'original_filename': original_filename,
            'created_at': datetime.now().isoformat(),
            # Store dual embeddings in metadata (pgvector supports custom embedding fields)
            '_embedding_facts': embedding_facts,
            '_embedding_metadata': embedding_metadata,
        }
        
        # Remove None values
        meta = {k: v for k, v in meta.items() if v is not None}
        
        # Use facts embedding as primary embedding (can be swapped for metadata-based search)
        primary_embedding = embedding_facts if embedding_facts else embedding_metadata
        
        return Document(
            id=doc_id,
            content=content,
            meta=meta,
            embedding=primary_embedding
        )
    
    @staticmethod
    def from_haystack_document(doc: Document) -> Dict[str, Any]:
        """
        Convert Haystack Document to CaseMind data structure.
        
        Args:
            doc: Haystack Document
            
        Returns:
            Dict with CaseMind-compatible structure
        """
        meta = doc.meta or {}
        
        return {
            'id': doc.id,
            'content': doc.content,
            'meta': {k: v for k, v in meta.items() if not k.startswith('_')},
            'file_hash': meta.get('file_hash'),
            'original_filename': meta.get('original_filename'),
            'created_at': meta.get('created_at'),
            'embedding_facts': meta.get('_embedding_facts'),
            'embedding_metadata': meta.get('_embedding_metadata'),
            'primary_embedding': doc.embedding
        }
    
    @staticmethod
    def to_haystack_documents_batch(
        documents: List[Dict[str, Any]]
    ) -> List[Document]:
        """
        Convert batch of CaseMind documents to Haystack Documents.
        
        Args:
            documents: List of dicts with keys: id, content, meta, embeddings, etc.
            
        Returns:
            List of Haystack Documents
        """
        haystack_docs = []
        for doc in documents:
            haystack_doc = HaystackDocumentConverter.to_haystack_document(
                doc_id=doc.get('id'),
                content=doc.get('content', ''),
                metadata=doc.get('meta', {}),
                embedding_facts=doc.get('embedding_facts'),
                embedding_metadata=doc.get('embedding_metadata'),
                file_hash=doc.get('file_hash'),
                original_filename=doc.get('original_filename')
            )
            haystack_docs.append(haystack_doc)
        
        return haystack_docs
    
    @staticmethod
    def extract_embeddings_for_field(
        doc: Document,
        field: str = 'facts'
    ) -> Optional[List[float]]:
        """
        Extract specific embedding field from Haystack Document.
        
        Args:
            doc: Haystack Document
            field: 'facts' or 'metadata'
            
        Returns:
            Embedding vector or None
        """
        if field == 'facts':
            return doc.meta.get('_embedding_facts', doc.embedding)
        elif field == 'metadata':
            return doc.meta.get('_embedding_metadata')
        else:
            return doc.embedding
