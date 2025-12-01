"""
FastAPI dependency injection functions.
Provides shared dependencies for routes.
"""

import sys
from pathlib import Path
from typing import AsyncGenerator

import asyncpg

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from api.database import db


async def get_db_connection() -> AsyncGenerator[asyncpg.Connection, None]:
    """
    Get database connection for route handlers.
    
    Yields:
        asyncpg.Connection
    """
    async with db.get_connection() as connection:
        yield connection
