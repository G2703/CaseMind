"""
PostgreSQL + pgvector document store implementation.
Uses Singleton pattern for connection management.
"""

import logging
from typing import Dict, List, Any, Optional
from pathlib import Path
import numpy as np
import psycopg2
from psycopg2.extras import RealDictCursor, Json
from psycopg2.extensions import register_adapter
import json

from core.interfaces import IDocumentStore
from core.exceptions import DatabaseConnectionError, DocumentStoreError
from core.config import Config

logger = logging.getLogger(__name__)

# Register numpy array adapter for PostgreSQL
register_adapter(np.ndarray, lambda array: Json(array.tolist()))


class PGVectorDocumentStore(IDocumentStore):
    """
    PostgreSQL + pgvector implementation of document store.
    Singleton pattern ensures single database connection.
    """
    
    _instance: Optional['PGVectorDocumentStore'] = None
    _initialized: bool = False
    
    def __new__(cls) -> 'PGVectorDocumentStore':
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not self._initialized:
            self.config = Config()
            self.connection = None
            self._connect()
            PGVectorDocumentStore._initialized = True
    
    def _connect(self) -> None:
        """Establish database connection."""
        try:
            self.connection = psycopg2.connect(
                host=self.config.db_host,
                port=self.config.db_port,
                database=self.config.db_name,
                user=self.config.db_user,
                password=self.config.db_password
            )
            self.connection.autocommit = False
            logger.info(f"Connected to PostgreSQL database: {self.config.db_name}")
        except psycopg2.Error as e:
            logger.error(f"Failed to connect to database: {e}")
            raise DatabaseConnectionError(f"Database connection failed: {e}")
    
    def ensure_pgvector_extension(self) -> None:
        """Ensure pgvector extension is installed."""
        try:
            # Use a fresh short-lived connection in autocommit mode to run
            # CREATE EXTENSION. This avoids errors when the main connection
            # is in an aborted transaction (e.g. due to earlier failed queries)
            params = dict(
                host=self.config.db_host,
                port=self.config.db_port,
                database=self.config.db_name,
                user=self.config.db_user,
                password=self.config.db_password,
            )
            temp_conn = None
            try:
                temp_conn = psycopg2.connect(**params)
                temp_conn.autocommit = True
                with temp_conn.cursor() as cursor:
                    cursor.execute("CREATE EXTENSION IF NOT EXISTS vector;")
                logger.info("pgvector extension ensured (via temp connection)")
            finally:
                if temp_conn:
                    try:
                        temp_conn.close()
                    except Exception:
                        pass
        except psycopg2.Error as e:
            # Attempt to rollback the primary connection if possible, then
            # surface a clear error.
            try:
                if self.connection:
                    self.connection.rollback()
            except Exception:
                pass
            logger.error(f"Failed to create pgvector extension: {e}")
            raise DocumentStoreError(f"pgvector extension error: {e}")
    
    def create_schema(self) -> None:
        """Create database schema with dual embeddings."""
        schema_sql = """
        CREATE TABLE IF NOT EXISTS haystack_documents (
            id VARCHAR(255) PRIMARY KEY,
            content TEXT NOT NULL,
            content_type VARCHAR(50) DEFAULT 'text',
            meta JSONB NOT NULL,
            embedding_facts vector(768) NOT NULL,
            embedding_metadata vector(768) NOT NULL,
            score FLOAT,
            file_hash VARCHAR(64) UNIQUE NOT NULL,
            original_filename VARCHAR(512),
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        );
        
        -- Vector similarity indexes
        CREATE INDEX IF NOT EXISTS idx_embedding_facts_ivfflat 
        ON haystack_documents 
        USING ivfflat (embedding_facts vector_cosine_ops)
        WITH (lists = 100);
        
        CREATE INDEX IF NOT EXISTS idx_embedding_metadata_ivfflat 
        ON haystack_documents 
        USING ivfflat (embedding_metadata vector_cosine_ops)
        WITH (lists = 100);
        
        -- Metadata indexes
        CREATE INDEX IF NOT EXISTS idx_meta_gin 
        ON haystack_documents USING gin (meta);
        
        CREATE INDEX IF NOT EXISTS idx_case_id 
        ON haystack_documents ((meta->>'case_id'));
        
        CREATE INDEX IF NOT EXISTS idx_file_hash 
        ON haystack_documents (file_hash);
        
        CREATE INDEX IF NOT EXISTS idx_template_id 
        ON haystack_documents ((meta->>'template_id'));
        
        CREATE INDEX IF NOT EXISTS idx_case_title 
        ON haystack_documents ((meta->>'case_title'));
        
        -- Trigger for updated_at
        CREATE OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = NOW();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        
        DROP TRIGGER IF EXISTS update_haystack_documents_updated_at ON haystack_documents;
        CREATE TRIGGER update_haystack_documents_updated_at
        BEFORE UPDATE ON haystack_documents
        FOR EACH ROW
        EXECUTE FUNCTION update_updated_at_column();
        """
        
        try:
            # If a previous operation left the main connection in an aborted
            # transaction state, rollback it so we can run schema creation.
            try:
                if self.connection:
                    self.connection.rollback()
            except Exception:
                # Best-effort rollback; continue to attempt schema creation.
                pass
            with self.connection.cursor() as cursor:
                cursor.execute(schema_sql)
            self.connection.commit()
            logger.info("Database schema created successfully")
        except psycopg2.Error as e:
            self.connection.rollback()
            logger.error(f"Failed to create schema: {e}")
            raise DocumentStoreError(f"Schema creation failed: {e}")
    
    def write_document(self, document: Dict[str, Any]) -> str:
        """Store a document with dual embeddings."""
        try:
            with self.connection.cursor() as cursor:
                # Convert numpy arrays to lists for JSON
                embedding_facts_list = document['embedding_facts'].tolist()
                embedding_metadata_list = document['embedding_metadata'].tolist()
                
                insert_sql = """
                INSERT INTO haystack_documents 
                (id, content, content_type, meta, embedding_facts, embedding_metadata, 
                 file_hash, original_filename)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (file_hash) DO NOTHING
                RETURNING id;
                """
                
                cursor.execute(insert_sql, (
                    document['id'],
                    document['content'],
                    document.get('content_type', 'text'),
                    json.dumps(document['meta']),
                    embedding_facts_list,
                    embedding_metadata_list,
                    document['file_hash'],
                    document['original_filename']
                ))
                
                result = cursor.fetchone()
                self.connection.commit()
                
                if result:
                    logger.info(f"Document stored: {document['id']}")
                    return result[0]
                else:
                    logger.warning(f"Document already exists (duplicate): {document['file_hash']}")
                    return None
                    
        except psycopg2.Error as e:
            self.connection.rollback()
            logger.error(f"Failed to write document: {e}")
            raise DocumentStoreError(f"Document write failed: {e}")
    
    def query_by_embedding(
        self,
        embedding: np.ndarray,
        top_k: int,
        embedding_field: str = "embedding_facts",
        exclude_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Query documents by embedding similarity."""
        try:
            embedding_list = embedding.tolist()
            
            # Build query with optional exclusion
            exclude_clause = "AND id != %s" if exclude_id else ""
            params = [json.dumps(embedding_list), top_k]
            if exclude_id:
                params.insert(1, exclude_id)
            
            query_sql = f"""
            SELECT 
                id,
                content,
                meta,
                file_hash,
                original_filename,
                created_at,
                1 - ({embedding_field} <=> %s::vector) AS similarity_score
            FROM haystack_documents
            WHERE 1=1 {exclude_clause}
            ORDER BY {embedding_field} <=> %s::vector
            LIMIT %s;
            """
            
            with self.connection.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(query_sql, params)
                results = cursor.fetchall()
                
            return [dict(row) for row in results]
            
        except psycopg2.Error as e:
            logger.error(f"Failed to query by embedding: {e}")
            raise DocumentStoreError(f"Embedding query failed: {e}")
    
    def get_document_by_id(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve document by ID."""
        try:
            query_sql = """
            SELECT id, content, meta, file_hash, original_filename, created_at
            FROM haystack_documents
            WHERE id = %s;
            """
            
            with self.connection.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(query_sql, (doc_id,))
                result = cursor.fetchone()
                
            return dict(result) if result else None
            
        except psycopg2.Error as e:
            logger.error(f"Failed to get document by ID: {e}")
            raise DocumentStoreError(f"Get document failed: {e}")
    
    def check_duplicate(self, file_hash: str) -> Optional[Dict[str, Any]]:
        """Check if document with given file hash exists."""
        try:
            query_sql = """
            SELECT id, meta->>'case_id' as case_id, meta->>'case_title' as case_title
            FROM haystack_documents
            WHERE file_hash = %s;
            """
            
            with self.connection.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(query_sql, (file_hash,))
                result = cursor.fetchone()
                
            return dict(result) if result else None
            
        except psycopg2.Error as e:
            logger.error(f"Failed to check duplicate: {e}")
            raise DocumentStoreError(f"Duplicate check failed: {e}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get database statistics."""
        try:
            stats_sql = """
            SELECT 
                COUNT(*) as total_documents,
                COUNT(DISTINCT meta->>'template_id') as unique_templates,
                MIN(created_at) as oldest_case,
                MAX(created_at) as newest_case
            FROM haystack_documents;
            """
            
            with self.connection.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(stats_sql)
                result = cursor.fetchone()
                
            return dict(result) if result else {}
            
        except psycopg2.Error as e:
            logger.error(f"Failed to get statistics: {e}")
            return {}
    
    def close(self) -> None:
        """Close database connection."""
        if self.connection:
            self.connection.close()
            logger.info("Database connection closed")
