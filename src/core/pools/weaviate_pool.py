"""
Weaviate connection pool for managing multiple connections.
Pre-initializes connections for parallel access.
"""

import asyncio
import logging
from typing import Optional
from contextlib import asynccontextmanager

from src.infrastructure.weaviate_client import WeaviateClient
from src.core.config import Config

logger = logging.getLogger(__name__)


class WeaviateConnectionPool:
    """
    Connection pool for Weaviate clients.
    Pre-initializes N connections for concurrent access.
    
    Note: Since WeaviateClient is a singleton, we share the same client
    instance but use a semaphore to control concurrent access.
    """
    
    def __init__(self, pool_size: int = 3, config: Optional[Config] = None):
        """
        Initialize connection pool.
        
        Args:
            pool_size: Number of concurrent connections allowed
            config: Configuration instance
        """
        self.pool_size = pool_size
        self.config = config or Config()
        self.client: Optional[WeaviateClient] = None
        self.semaphore: Optional[asyncio.Semaphore] = None
        self._initialized = False
        
        logger.info(f"WeaviateConnectionPool created with pool_size {pool_size}")
    
    async def initialize(self) -> None:
        """Initialize the shared Weaviate client."""
        if self._initialized:
            logger.warning("WeaviateConnectionPool already initialized")
            return
        
        logger.info("Initializing Weaviate client connection...")
        
        try:
            # Initialize the singleton client (no config parameter needed)
            self.client = WeaviateClient()
            
            # Verify connection
            if not self.client.is_ready():
                raise RuntimeError("Weaviate client not ready")
            
            # Create semaphore to control concurrent access
            self.semaphore = asyncio.Semaphore(self.pool_size)
            
            self._initialized = True
            logger.info(f"✓ WeaviateConnectionPool initialized (pool_size: {self.pool_size})")
            
        except Exception as e:
            logger.error(f"Failed to initialize connection pool: {e}")
            raise
    
    @asynccontextmanager
    async def acquire(self):
        """
        Acquire a connection from the pool.
        Uses semaphore to limit concurrent access to the shared client.
        
        Usage:
            async with pool.acquire() as client:
                # Use client
                pass
        """
        if not self._initialized:
            raise RuntimeError("Pool not initialized. Call initialize() first.")
        
        # Acquire semaphore (blocks if pool_size connections already in use)
        async with self.semaphore:
            logger.debug("Connection acquired from pool")
            try:
                yield self.client
            finally:
                logger.debug("Connection released to pool")
    
    async def close(self) -> None:
        """Close the Weaviate client connection."""
        logger.info("Closing WeaviateConnectionPool...")
        
        if self.client:
            try:
                self.client.close()
            except Exception as e:
                logger.warning(f"Error closing connection: {e}")
        
        self.client = None
        self.semaphore = None
        self._initialized = False
        logger.info("✓ WeaviateConnectionPool closed")
    
    def get_status(self) -> dict:
        """Get pool status."""
        available = self.semaphore._value if self.semaphore else 0
        in_use = self.pool_size - available if self.semaphore else 0
        
        return {
            "pool_size": self.pool_size,
            "initialized": self._initialized,
            "connections_in_use": in_use,
            "connections_available": available,
            "client_ready": self.client.is_ready() if self.client else False
        }
