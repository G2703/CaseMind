"""Schemas package initialization."""

from api.schemas.common import ErrorResponse, SuccessResponse, PaginatedResponse
from api.schemas.session import (
    SessionCreateResponse,
    SessionStatusResponse,
    SearchParams,
    SimilarCaseItem,
    QueryCaseData,
    SearchResultsResponse
)
from api.schemas.cases import (
    CaseMetadataResponse,
    CaseSummaryResponse,
    FactsResponse,
    CaseDetailResponse,
    CaseListItem,
    ComparisonResponse
)

__all__ = [
    "ErrorResponse",
    "SuccessResponse",
    "PaginatedResponse",
    "SessionCreateResponse",
    "SessionStatusResponse",
    "SearchParams",
    "SimilarCaseItem",
    "QueryCaseData",
    "SearchResultsResponse",
    "CaseMetadataResponse",
    "CaseSummaryResponse",
    "FactsResponse",
    "CaseDetailResponse",
    "CaseListItem",
    "ComparisonResponse",
]
