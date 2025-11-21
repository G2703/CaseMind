"""
Haystack-based Document Store for CaseMind using PgvectorDocumentStore.
Wraps Haystack's PgvectorDocumentStore with custom logic for dual embeddings.
"""

import logging
import os
import json
import numpy as np
from typing import List, Dict, Any, Optional
from datetime import datetime
from haystack import Document
from haystack_integrations.document_stores.pgvector import PgvectorDocumentStore
from haystack_integrations.components.retrievers.pgvector import PgvectorEmbeddingRetriever

from infrastructure.haystack_document_converter import HaystackDocumentConverter
from core.config import Config

logger = logging.getLogger(__name__)


class DocumentStoreError(Exception):
    """Custom exception for document store errors."""
    pass


class HaystackDocumentStoreWrapper:
    """
    Wrapper around Haystack's PgvectorDocumentStore with CaseMind-specific logic.
    
    Features:
    - Dual embedding support (facts + metadata stored in meta fields)
    - Backward compatibility with existing code
    - Custom retrieval methods for facts vs metadata search
    - Integration with Haystack components ecosystem
    """
    
    _instance = None  # Singleton pattern
    
    def __new__(cls):
        """Ensure singleton instance."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Initialize Haystack PgvectorDocumentStore."""
        if self._initialized:
            return
            
        self.config = Config()
        
        # Build PostgreSQL connection string
        conn_str = self._build_connection_string()
        
        # Initialize Haystack PgvectorDocumentStore
        self.store = PgvectorDocumentStore(
            connection_string=conn_str,
            table_name="haystack_documents",
            embedding_dimension=768,  # sentence-transformers/all-mpnet-base-v2
            vector_function="cosine_similarity",
            recreate_table=False,  # Preserve existing data
            search_strategy="hnsw",  # HNSW for fast approximate search
            hnsw_recreate_index_if_exists=False,
            hnsw_index_creation_kwargs={
                "m": 16,  # Number of connections per layer
                "ef_construction": 64  # Size of dynamic candidate list
            }
        )
        
        self.converter = HaystackDocumentConverter()
        self._initialized = True
        
        logger.info(f"Haystack PgvectorDocumentStore initialized with table: haystack_documents")
    
    def _build_connection_string(self) -> str:
        """Build PostgreSQL connection string from config."""
        host = self.config.get("POSTGRES_HOST", "localhost")
        port = self.config.get("POSTGRES_PORT", "5432")
        user = self.config.get("POSTGRES_USER", "postgres")
        password = self.config.get("POSTGRES_PASSWORD", "postgres")
        database = self.config.get("POSTGRES_DB", "casemind")
        
        conn_str = f"postgresql://{user}:{password}@{host}:{port}/{database}"
        logger.debug(f"PostgreSQL connection string built for {host}:{port}/{database}")
        
        return conn_str
    
    def write_document(
        self,
        doc_id: str,
        content: str,
        metadata: Dict[str, Any],
        embedding_facts: np.ndarray,
        embedding_metadata: np.ndarray,
        file_hash: str,
        original_filename: str
    ) -> str:
        """
        Write document with dual embeddings to document store.
        
        Args:
            doc_id: Unique document ID (case_id)
            content: Full text content
            metadata: Case metadata dict
            embedding_facts: Facts embedding vector (768-dim)
            embedding_metadata: Metadata embedding vector (768-dim)
            file_hash: SHA-256 hash of source PDF
            original_filename: Original PDF filename
            
        Returns:
            Document ID
        """
        try:
            # Convert numpy arrays to lists
            facts_list = embedding_facts.tolist() if isinstance(embedding_facts, np.ndarray) else embedding_facts
            metadata_list = embedding_metadata.tolist() if isinstance(embedding_metadata, np.ndarray) else embedding_metadata
            
            # Create Haystack Document with dual embeddings in metadata
            doc = self.converter.to_haystack_document(
                doc_id=doc_id,
                content=content,
                metadata=metadata,
                embedding_facts=facts_list,
                embedding_metadata=metadata_list,
                file_hash=file_hash,
                original_filename=original_filename
            )
            
            # Check if document exists (for duplicate handling)
            existing_docs = self.store.filter_documents(filters={"field": "meta.file_hash", "operator": "==", "value": file_hash})
            
            if existing_docs:
                logger.debug(f"Document with file_hash {file_hash} already exists. Skipping write.")
                return existing_docs[0].id
            
            # Write to Haystack store
            self.store.write_documents([doc], policy="skip")  # skip if exists
            
            logger.info(f"Document {doc_id} written to Haystack document store")
            return doc_id
            
        except Exception as e:
            logger.error(f"Failed to write document: {e}")
            raise DocumentStoreError(f"Failed to write document: {e}")
    
    def query_by_embedding(
        self,
        embedding: np.ndarray,
        top_k: int,
        embedding_field: str = "embedding_facts",
        exclude_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Query documents by embedding similarity.
        
        Args:
            embedding: Query embedding vector
            top_k: Number of results to return
            embedding_field: 'embedding_facts' or 'embedding_metadata'
            exclude_id: Optional document ID to exclude from results
            
        Returns:
            List of document dicts with similarity scores
        """
        try:
            # Convert numpy to list
            query_embedding = embedding.tolist() if isinstance(embedding, np.ndarray) else embedding
            
            # Build filters to exclude specific document
            filters = None
            if exclude_id:
                filters = {"field": "id", "operator": "!=", "value": exclude_id}
            
            # For facts embedding, use primary embedding field
            if embedding_field == "embedding_facts":
                # Use direct retrieval (Haystack uses primary embedding)
                results = self.store._embedding_retrieval(
                    query_embedding=query_embedding,
                    top_k=top_k,
                    filters=filters
                )
            else:
                # For metadata embedding, need custom retrieval
                # This is a limitation - Haystack primarily uses one embedding per doc
                # Workaround: retrieve all and re-rank using metadata embedding from meta
                logger.warning("Metadata embedding search uses fallback method - consider using separate table")
                results = self._custom_metadata_retrieval(query_embedding, top_k, exclude_id)
            
            # Convert to CaseMind format
            output = []
            for doc in results:
                converted = self.converter.from_haystack_document(doc)
                converted['similarity_score'] = doc.score if hasattr(doc, 'score') else 0.0
                output.append(converted)
            
            return output
            
        except Exception as e:
            logger.error(f"Failed to query by embedding: {e}")
            raise DocumentStoreError(f"Embedding query failed: {e}")
    
    def _custom_metadata_retrieval(
        self,
        query_embedding: List[float],
        top_k: int,
        exclude_id: Optional[str] = None
    ) -> List[Document]:
        """
        Custom retrieval using metadata embeddings stored in meta field.
        Note: This is less efficient than native pgvector search.
        """
        # Get all documents (or use a broader search)
        all_docs = self.store.filter_documents(filters=None)
        
        # Calculate cosine similarity with metadata embeddings
        scored_docs = []
        query_np = np.array(query_embedding)
        
        for doc in all_docs:
            if exclude_id and doc.id == exclude_id:
                continue
                
            meta_embedding = doc.meta.get('_embedding_metadata')
            if meta_embedding:
                meta_np = np.array(meta_embedding)
                similarity = np.dot(query_np, meta_np) / (np.linalg.norm(query_np) * np.linalg.norm(meta_np))
                doc.score = float(similarity)
                scored_docs.append(doc)
        
        # Sort by similarity and return top_k
        scored_docs.sort(key=lambda x: x.score, reverse=True)
        return scored_docs[:top_k]
    
    def get_document_by_id(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve document by ID."""
        try:
            docs = self.store.filter_documents(filters={"field": "id", "operator": "==", "value": doc_id})
            
            if docs:
                return self.converter.from_haystack_document(docs[0])
            return None
            
        except Exception as e:
            logger.error(f"Failed to get document by ID: {e}")
            return None
    
    def get_embedding_by_id(
        self,
        doc_id: str,
        embedding_field: str = 'embedding_facts'
    ) -> Optional[np.ndarray]:
        """
        Retrieve embedding vector for a document by ID.
        
        Args:
            doc_id: Document ID
            embedding_field: 'embedding_facts' or 'embedding_metadata'
            
        Returns:
            numpy array of embedding or None
        """
        try:
            doc_dict = self.get_document_by_id(doc_id)
            
            if doc_dict:
                if embedding_field == 'embedding_facts':
                    emb = doc_dict.get('embedding_facts')
                else:
                    emb = doc_dict.get('embedding_metadata')
                
                if emb:
                    return np.array(emb, dtype=np.float32)
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get embedding by ID: {e}")
            return None
    
    def check_duplicate(self, file_hash: str) -> Optional[Dict[str, Any]]:
        """Check if document with given file hash exists."""
        try:
            docs = self.store.filter_documents(
                filters={"field": "meta.file_hash", "operator": "==", "value": file_hash}
            )
            
            if docs:
                doc = docs[0]
                return {
                    'exists': True,
                    'document_id': doc.id,
                    'case_id': doc.meta.get('case_id'),
                    'case_title': doc.meta.get('case_title')
                }
            
            return {'exists': False}
            
        except Exception as e:
            logger.error(f"Duplicate check failed: {e}")
            return {'exists': False}
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get document store statistics."""
        try:
            total_docs = self.store.count_documents()
            
            # Get unique templates (most_appropriate_section)
            all_docs = self.store.filter_documents(filters=None)
            unique_templates = set()
            for doc in all_docs:
                template = doc.meta.get('most_appropriate_section')
                if template:
                    unique_templates.add(template)
            
            return {
                'total_documents': total_docs,
                'unique_templates': len(unique_templates),
                'backend': 'Haystack PgvectorDocumentStore'
            }
            
        except Exception as e:
            logger.error(f"Failed to get statistics: {e}")
            return {
                'total_documents': 0,
                'unique_templates': 0,
                'backend': 'Haystack PgvectorDocumentStore (error)'
            }
    
    def delete_document(self, doc_id: str) -> bool:
        """Delete document by ID."""
        try:
            self.store.delete_documents([doc_id])
            logger.info(f"Deleted document {doc_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete document: {e}")
            return False
    
    def get_haystack_store(self) -> PgvectorDocumentStore:
        """
        Get underlying Haystack PgvectorDocumentStore for direct access.
        Useful for building Haystack Pipelines.
        """
        return self.store


# Backward compatibility alias
PGVectorDocumentStore = HaystackDocumentStoreWrapper
