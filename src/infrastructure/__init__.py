"""
Infrastructure layer for external integrations.
Handles Weaviate, storage, and other external systems.
"""

from .weaviate_client import WeaviateClient
from .weaviate_schema import (
    CASE_DOCUMENTS_SCHEMA,
    CASE_METADATA_SCHEMA,
    CASE_SECTIONS_SCHEMA,
    CASE_CHUNKS_SCHEMA,
    ALL_SCHEMAS,
)
from .storage_adapter import LocalStorageAdapter

__all__ = [
    'WeaviateClient',
    'LocalStorageAdapter',
    'CASE_DOCUMENTS_SCHEMA',
    'CASE_METADATA_SCHEMA',
    'CASE_SECTIONS_SCHEMA',
    'CASE_CHUNKS_SCHEMA',
    'ALL_SCHEMAS',
]
