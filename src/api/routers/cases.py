"""
Cases router - read-only access to legal_cases database.
Provides case retrieval, filtering, and comparison functionality.
"""

import logging
from typing import Optional, List
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
import asyncpg

from api.dependencies import get_db_connection
from api.schemas import (
    CaseDetailResponse,
    CaseSummaryResponse,
    FactsResponse,
    CaseListItem,
    ComparisonResponse,
    PaginatedResponse
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/", response_model=PaginatedResponse)
async def list_cases(
    skip: int = Query(0, ge=0, description="Number of cases to skip"),
    limit: int = Query(20, ge=1, le=100, description="Maximum cases to return"),
    section: Optional[str] = Query(None, description="Filter by legal section"),
    court: Optional[str] = Query(None, description="Filter by court name"),
    date_from: Optional[date] = Query(None, description="Filter from date"),
    date_to: Optional[date] = Query(None, description="Filter to date"),
    db: asyncpg.Connection = Depends(get_db_connection)
):
    """
    List all cases with pagination and optional filtering.
    
    Currently 23 cases in database. Useful for browsing available cases.
    """
    # TODO: Implement in Day 6
    raise HTTPException(status_code=501, detail="Not implemented yet")


@router.get("/{file_id}", response_model=CaseDetailResponse)
async def get_case_detail(
    file_id: str,
    db: asyncpg.Connection = Depends(get_db_connection)
) -> CaseDetailResponse:
    """
    Get complete case information including summary and facts.
    
    Returns all data from legal_cases table for the specified file_id.
    """
    # TODO: Implement in Day 6
    raise HTTPException(status_code=501, detail="Not implemented yet")


@router.get("/{file_id}/summary", response_model=CaseSummaryResponse)
async def get_case_summary(
    file_id: str,
    db: asyncpg.Connection = Depends(get_db_connection)
) -> CaseSummaryResponse:
    """
    Get only the 7-section summary (lighter response than full details).
    
    Sections: metadata, case_facts, issues, evidence, arguments, reasoning, judgement
    """
    # TODO: Implement in Day 6
    raise HTTPException(status_code=501, detail="Not implemented yet")


@router.get("/{file_id}/facts", response_model=FactsResponse)
async def get_case_facts(
    file_id: str,
    db: asyncpg.Connection = Depends(get_db_connection)
) -> FactsResponse:
    """
    Get template-extracted facts (4-tier structure).
    
    Tiers: tier_1_parties, tier_2_incident, tier_3_legal, tier_4_procedural
    """
    # TODO: Implement in Day 6
    raise HTTPException(status_code=501, detail="Not implemented yet")


@router.get("/{file_id}/compare/{other_file_id}", response_model=ComparisonResponse)
async def compare_cases(
    file_id: str,
    other_file_id: str,
    db: asyncpg.Connection = Depends(get_db_connection)
) -> ComparisonResponse:
    """
    Compare two cases side-by-side.
    
    Returns both cases with highlighted common sections and fact differences.
    """
    # TODO: Implement in Day 6
    raise HTTPException(status_code=501, detail="Not implemented yet")
