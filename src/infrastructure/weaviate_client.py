"""
Weaviate client manager with singleton pattern.
Provides centralized connection management for Weaviate database.
"""

import weaviate
from weaviate.classes.init import AdditionalConfig, Timeout
from typing import Optional
import logging
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from src.core.config import Config

logger = logging.getLogger(__name__)


class WeaviateClient:
    """Singleton Weaviate client manager."""
    
    _instance: Optional['WeaviateClient'] = None
    _client: Optional[weaviate.WeaviateClient] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._client is None:
            self._initialize_client()
    
    def _initialize_client(self):
        """Initialize Weaviate client connection."""
        config = Config()
        
        try:
            # Extract host and port from URL
            url = config.weaviate_url
            if '://' in url:
                url = url.split('://')[-1]
            
            host = url.split(':')[0] if ':' in url else url
            http_port = int(url.split(':')[1]) if ':' in url and url.split(':')[1] else 8080
            
            logger.info(f"Connecting to Weaviate at {host}:{http_port}")
            
            # Connect to local Weaviate instance
            self._client = weaviate.connect_to_local(
                host=host,
                port=http_port,
                grpc_port=config.weaviate_grpc_port,
                additional_config=AdditionalConfig(
                    timeout=Timeout(init=config.weaviate_timeout, query=config.weaviate_timeout, insert=config.weaviate_timeout)
                )
            )
            
            # Verify connection
            if self._client.is_ready():
                logger.info("✓ Weaviate client initialized successfully")
            else:
                logger.error("✗ Weaviate client not ready")
                
        except Exception as e:
            logger.error(f"Failed to initialize Weaviate client: {e}")
            raise
    
    @property
    def client(self) -> weaviate.WeaviateClient:
        """Get Weaviate client instance."""
        if self._client is None:
            self._initialize_client()
        return self._client
    
    def is_ready(self) -> bool:
        """Check if Weaviate is ready."""
        try:
            return self._client is not None and self._client.is_ready()
        except Exception as e:
            logger.error(f"Weaviate health check failed: {e}")
            return False
    
    def get_meta(self) -> dict:
        """Get Weaviate cluster metadata."""
        try:
            if self._client:
                meta = self._client.get_meta()
                return meta
            return {}
        except Exception as e:
            logger.error(f"Failed to get Weaviate metadata: {e}")
            return {}
    
    def close(self):
        """Close Weaviate connection."""
        if self._client:
            try:
                self._client.close()
                logger.info("Weaviate client connection closed")
            except Exception as e:
                logger.error(f"Error closing Weaviate client: {e}")
            finally:
                self._client = None
    
    def __del__(self):
        """Cleanup on deletion."""
        self.close()
