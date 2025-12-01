"""Common Pydantic schemas used across API endpoints."""

from typing import Optional, Any, Dict, List
from pydantic import BaseModel, Field


class ErrorResponse(BaseModel):
    """Standard error response."""
    error: str = Field(..., description="Error type")
    detail: str = Field(..., description="Error details")
    field: Optional[str] = Field(None, description="Field that caused error (if applicable)")


class SuccessResponse(BaseModel):
    """Standard success response."""
    success: bool = Field(True, description="Operation success status")
    message: str = Field(..., description="Success message")
    data: Optional[Dict[str, Any]] = Field(None, description="Additional data")


class PaginatedResponse(BaseModel):
    """Paginated response wrapper."""
    items: List[Any] = Field(..., description="List of items")
    total: int = Field(..., description="Total number of items")
    skip: int = Field(..., description="Number of items skipped")
    limit: int = Field(..., description="Maximum items per page")
    has_more: bool = Field(..., description="Whether more items are available")
