"""
Core module - configuration, models, and exceptions.
"""

from .config import Config
from .models import (
    ProcessingStatus,
    MatchMethod,
    CaseMetadata,
    Template,
    ExtractedFacts,
    DuplicateStatus,
    IngestResult,
    BatchIngestResult,
    SimilarCase,
    SimilaritySearchResult
)
from .exceptions import *

__all__ = [
    'Config',
    'ProcessingStatus',
    'MatchMethod',
    'CaseMetadata',
    'Template',
    'ExtractedFacts',
    'DuplicateStatus',
    'IngestResult',
    'BatchIngestResult',
    'SimilarCase',
    'SimilaritySearchResult'
]
