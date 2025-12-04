"""
Service layer for CaseMind.
Only contains ExtractionService - other services have been integrated into Haystack components.
"""

from .extraction_service import ExtractionService

__all__ = [
    'ExtractionService',
]
