"""Pydantic schemas for case data operations."""

from datetime import datetime
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field


class CaseMetadataResponse(BaseModel):
    """Case metadata from summary."""
    case_number: Optional[str] = Field(None, description="Court case number")
    case_title: str = Field(..., description="Case title")
    court_name: str = Field(..., description="Court name")
    judgment_date: str = Field(..., description="Judgment date")
    sections_invoked: List[str] = Field(..., description="All legal sections")
    most_appropriate_section: str = Field(..., description="Primary section")
    appellant_or_petitioner: Optional[str] = Field(None, description="Appellant/Petitioner")
    respondent: Optional[str] = Field(None, description="Respondent")


class CaseSummaryResponse(BaseModel):
    """7-section case summary."""
    file_id: str = Field(..., description="Case identifier")
    metadata: Dict[str, Any] = Field(..., description="Case metadata")
    case_facts: Dict[str, Any] = Field(..., description="Case facts section")
    issues: List[str] = Field(..., description="Issues for determination")
    evidence: Dict[str, Any] = Field(..., description="Evidence presented")
    arguments: Dict[str, Any] = Field(..., description="Arguments")
    reasoning: Dict[str, Any] = Field(..., description="Court reasoning")
    judgement: Dict[str, Any] = Field(..., description="Final judgment")


class FactsResponse(BaseModel):
    """Template-extracted 4-tier facts."""
    file_id: str = Field(..., description="Case identifier")
    template_id: str = Field(..., description="Template used")
    template_label: str = Field(..., description="Template label")
    template_confidence: float = Field(..., description="Template match confidence")
    facts: Dict[str, Any] = Field(..., description="4-tier facts structure")


class CaseDetailResponse(BaseModel):
    """Complete case information."""
    file_id: str = Field(..., description="Case identifier")
    case_id: Optional[str] = Field(None, description="Court case number")
    case_title: str = Field(..., description="Case title")
    original_filename: str = Field(..., description="Original PDF filename")
    ingestion_timestamp: datetime = Field(..., description="When case was ingested")
    summary: Dict[str, Any] = Field(..., description="Full 7-section summary")
    factual_summary: Dict[str, Any] = Field(..., description="Template-extracted facts")


class CaseListItem(BaseModel):
    """Brief case information for list view."""
    file_id: str = Field(..., description="Case identifier")
    case_title: str = Field(..., description="Case title")
    court_name: str = Field(..., description="Court name")
    judgment_date: str = Field(..., description="Judgment date")
    most_appropriate_section: str = Field(..., description="Primary section")
    ingestion_timestamp: datetime = Field(..., description="Ingestion time")


class ComparisonResponse(BaseModel):
    """Side-by-side case comparison."""
    case_1: CaseDetailResponse = Field(..., description="First case")
    case_2: CaseDetailResponse = Field(..., description="Second case")
    similarity_score: Optional[float] = Field(None, description="Similarity score between cases")
    common_sections: List[str] = Field(..., description="Sections common to both cases")
    fact_differences: Dict[str, Any] = Field(..., description="Differences in facts")
