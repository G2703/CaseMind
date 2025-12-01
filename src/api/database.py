"""
Database connection management for FastAPI application.
Provides async database connection pool using asyncpg.
"""

import sys
import logging
from pathlib import Path
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import asyncpg
from asyncpg.pool import Pool

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.config import Config


logger = logging.getLogger(__name__)


class Database:
    """Database connection pool manager."""
    
    def __init__(self):
        """Initialize database configuration."""
        self.config = Config()
        self.pool: Pool = None
        
    async def connect(self) -> None:
        """Create database connection pool."""
        try:
            self.pool = await asyncpg.create_pool(
                host=self.config.db_host,
                port=self.config.db_port,
                database=self.config.db_name,
                user=self.config.db_user,
                password=self.config.db_password,
                min_size=5,
                max_size=20,
                command_timeout=60
            )
            logger.info("Database connection pool created")
        except Exception as e:
            logger.error(f"Failed to create database pool: {e}")
            raise
    
    async def disconnect(self) -> None:
        """Close database connection pool."""
        if self.pool:
            await self.pool.close()
            logger.info("Database connection pool closed")
    
    @asynccontextmanager
    async def get_connection(self) -> AsyncGenerator[asyncpg.Connection, None]:
        """
        Get database connection from pool.
        
        Yields:
            Database connection
        """
        if not self.pool:
            raise RuntimeError("Database pool not initialized")
        
        async with self.pool.acquire() as connection:
            yield connection


# Global database instance
db = Database()


async def get_db() -> AsyncGenerator[asyncpg.Connection, None]:
    """
    Dependency for FastAPI routes to get database connection.
    
    Yields:
        Database connection
    """
    async with db.get_connection() as connection:
        yield connection
