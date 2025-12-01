"""
Health router - system status, statistics, and filter options.
Provides read-only system information and database statistics.
"""

import logging
from typing import List, Dict, Any

from fastapi import APIRouter, Depends
import asyncpg

from api.dependencies import get_db_connection

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/health")
async def health_check(
    db: asyncpg.Connection = Depends(get_db_connection)
) -> Dict[str, Any]:
    """
    System health check.
    
    Returns:
    - API status
    - Database connectivity
    - Number of cases in legal_cases
    - Active search sessions count
    - Version information
    """
    try:
        # Check database
        db_status = "connected"
        
        # Count legal_cases
        legal_cases_count = await db.fetchval("SELECT COUNT(*) FROM legal_cases")
        
        # Count active sessions
        active_sessions = await db.fetchval(
            "SELECT COUNT(*) FROM search_sessions WHERE status != 'completed' AND status != 'failed'"
        )
        
        return {
            "status": "healthy",
            "database": db_status,
            "legal_cases_count": legal_cases_count,
            "active_sessions": active_sessions,
            "version": "1.0.0"
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "database": "disconnected",
            "error": str(e)
        }


@router.get("/stats")
async def get_statistics(
    db: asyncpg.Connection = Depends(get_db_connection)
) -> Dict[str, Any]:
    """
    Get database statistics.
    
    Returns aggregate information about cases in the database.
    """
    # TODO: Implement in Day 7
    return {
        "total_cases": 0,
        "unique_templates": 0,
        "date_range": {"earliest": None, "latest": None},
        "top_sections": [],
        "court_distribution": {},
        "database_size_mb": 0
    }


@router.get("/filters/sections")
async def get_available_sections(
    db: asyncpg.Connection = Depends(get_db_connection)
) -> List[str]:
    """
    Get all unique legal sections from legal_cases database.
    
    Used to populate filter dropdowns in frontend.
    """
    # TODO: Implement in Day 7
    return []


@router.get("/filters/courts")
async def get_available_courts(
    db: asyncpg.Connection = Depends(get_db_connection)
) -> List[str]:
    """
    Get all unique court names from legal_cases database.
    
    Used to populate filter dropdowns in frontend.
    """
    # TODO: Implement in Day 7
    return []


@router.get("/filters/templates")
async def get_available_templates(
    db: asyncpg.Connection = Depends(get_db_connection)
) -> List[Dict[str, Any]]:
    """
    Get all template types used in the database with counts.
    
    Returns template_id, template_label, and count of cases using each.
    """
    # TODO: Implement in Day 7
    return []
