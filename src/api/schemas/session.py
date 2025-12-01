"""Pydantic schemas for search session operations."""

from datetime import datetime
from typing import Optional, Dict, Any, List
from uuid import UUID
from pydantic import BaseModel, Field


class SessionCreateResponse(BaseModel):
    """Response after file upload (session creation)."""
    session_id: UUID = Field(..., description="Unique session identifier")
    filename: str = Field(..., description="Uploaded filename")
    file_size: int = Field(..., description="File size in bytes")
    status: str = Field(..., description="Initial status (uploaded)")
    created_at: datetime = Field(..., description="Session creation timestamp")


class SessionStatusResponse(BaseModel):
    """Real-time processing status response."""
    session_id: UUID = Field(..., description="Session identifier")
    status: str = Field(..., description="Current status (uploaded, processing, completed, failed)")
    current_phase: Optional[str] = Field(None, description="Current processing phase")
    current_step: Optional[str] = Field(None, description="Current processing step")
    progress_percentage: int = Field(..., description="Progress (0-100)")
    estimated_time_remaining: Optional[int] = Field(None, description="Estimated seconds remaining")
    error: Optional[str] = Field(None, description="Error message if failed")
    created_at: datetime = Field(..., description="Session creation time")
    updated_at: datetime = Field(..., description="Last update time")


class SearchParams(BaseModel):
    """Search parameters for result customization."""
    top_k: int = Field(5, ge=1, le=20, description="Number of results to return")
    threshold: float = Field(0.0, ge=0.0, le=1.0, description="Minimum similarity score")


class SimilarCaseItem(BaseModel):
    """Individual similar case in results."""
    file_id: str = Field(..., description="Case file identifier")
    case_title: str = Field(..., description="Case title")
    court_name: str = Field(..., description="Court name")
    judgment_date: str = Field(..., description="Judgment date")
    sections_invoked: List[str] = Field(..., description="Legal sections invoked")
    most_appropriate_section: str = Field(..., description="Primary section")
    similarity_score: float = Field(..., description="Cosine similarity score")
    cross_encoder_score: float = Field(..., description="Cross-encoder reranking score")
    rank: int = Field(..., description="Result rank (1-based)")


class QueryCaseData(BaseModel):
    """Query case summary and facts."""
    filename: str = Field(..., description="Uploaded filename")
    summary: Dict[str, Any] = Field(..., description="7-section summary")
    facts: Dict[str, Any] = Field(..., description="4-tier extracted facts")
    file_hash: str = Field(..., description="File hash (for duplicate detection)")


class SearchResultsResponse(BaseModel):
    """Complete search results response."""
    session_id: UUID = Field(..., description="Session identifier")
    query_case: QueryCaseData = Field(..., description="Uploaded case data")
    similar_cases: List[SimilarCaseItem] = Field(..., description="List of similar cases")
    total_results: int = Field(..., description="Number of results returned")
    search_params: SearchParams = Field(..., description="Search parameters used")
    is_duplicate: bool = Field(..., description="Whether query case already exists in database")
    duplicate_of_file_id: Optional[str] = Field(None, description="Existing case ID if duplicate")
