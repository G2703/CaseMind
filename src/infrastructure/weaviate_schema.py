"""
Weaviate collection schemas for CaseMind.
4 collections: CaseDocuments, CaseMetadata, CaseSections, CaseChunks
"""

from typing import Dict, Any, List


# Collection 1: CaseDocuments (file metadata, no vectors)
CASE_DOCUMENTS_SCHEMA: Dict[str, Any] = {
    "class": "CaseDocuments",
    "description": "Legal case document metadata and file references",
    "vectorizer": "none",
    "properties": [
        {
            "name": "file_id",
            "dataType": ["text"],
            "description": "Deterministic UUID from md_hash",
            "indexFilterable": True,
            "indexSearchable": False,
        },
        {
            "name": "md_hash",
            "dataType": ["text"],
            "description": "SHA256 hash of normalized markdown",
            "indexFilterable": True,
            "indexSearchable": False,
        },
        {
            "name": "original_filename",
            "dataType": ["text"],
            "description": "Original PDF filename",
            "indexFilterable": False,
            "indexSearchable": True,
        },
        {
            "name": "original_path",
            "dataType": ["text"],
            "description": "Original file path",
            "indexFilterable": False,
            "indexSearchable": False,
        },
        {
            "name": "md_gcs_uri",
            "dataType": ["text"],
            "description": "Local storage URI for markdown file",
            "indexFilterable": False,
            "indexSearchable": False,
        },
        {
            "name": "created_at",
            "dataType": ["date"],
            "description": "Document creation timestamp",
        },
        {
            "name": "updated_at",
            "dataType": ["date"],
            "description": "Last update timestamp",
        },
        {
            "name": "page_count",
            "dataType": ["int"],
            "description": "Number of pages in PDF",
        },
        {
            "name": "extraction_method",
            "dataType": ["text"],
            "description": "Method used for PDF extraction",
        },
    ],
}


# Collection 2: CaseMetadata (legal metadata, no vectors)
CASE_METADATA_SCHEMA: Dict[str, Any] = {
    "class": "CaseMetadata",
    "description": "Legal metadata for cases",
    "vectorizer": "none",
    "properties": [
        {
            "name": "metadata_id",
            "dataType": ["text"],
            "description": "Deterministic UUID: {file_id}::metadata",
            "indexFilterable": True,
        },
        {
            "name": "file_id",
            "dataType": ["text"],
            "description": "Links to CaseDocuments.file_id",
            "indexFilterable": True,
        },
        {
            "name": "case_number",
            "dataType": ["text"],
            "description": "Case number with year",
            "indexFilterable": True,
            "indexSearchable": True,
        },
        {
            "name": "case_title",
            "dataType": ["text"],
            "description": "Full case title",
            "indexFilterable": False,
            "indexSearchable": True,
        },
        {
            "name": "court_name",
            "dataType": ["text"],
            "description": "Name of the court",
            "indexFilterable": True,
            "indexSearchable": True,
        },
        {
            "name": "judgment_date",
            "dataType": ["date"],
            "description": "Date of judgment",
        },
        {
            "name": "appellant_or_petitioner",
            "dataType": ["text"],
            "description": "Appellant/petitioner name",
            "indexSearchable": True,
        },
        {
            "name": "respondent",
            "dataType": ["text"],
            "description": "Respondent name",
            "indexSearchable": True,
        },
        {
            "name": "judges_coram",
            "dataType": ["text[]"],
            "description": "Array of judge names",
        },
        {
            "name": "counsel_for_appellant",
            "dataType": ["text"],
            "description": "Appellant's counsel",
        },
        {
            "name": "counsel_for_respondent",
            "dataType": ["text"],
            "description": "Respondent's counsel",
        },
        {
            "name": "sections_invoked",
            "dataType": ["text[]"],
            "description": "Array of IPC/legal sections",
        },
        {
            "name": "most_appropriate_section",
            "dataType": ["text"],
            "description": "Primary applicable section",
            "indexFilterable": True,
        },
        {
            "name": "case_type",
            "dataType": ["text"],
            "description": "Type of case",
            "indexFilterable": True,
        },
        {
            "name": "citation",
            "dataType": ["text"],
            "description": "Legal citation",
            "indexSearchable": True,
        },
    ],
}


# Collection 3: CaseSections (9 sections with vectors)
CASE_SECTIONS_SCHEMA: Dict[str, Any] = {
    "class": "CaseSections",
    "description": "Legal case sections with embeddings",
    "vectorizer": "none",  # We provide vectors manually
    "vectorIndexConfig": {
        "distance": "cosine",
        "ef": -1,  # Dynamic ef
        "efConstruction": 200,
        "maxConnections": 32,
    },
    "properties": [
        {
            "name": "section_id",
            "dataType": ["text"],
            "description": "Deterministic UUID: {file_id}::{section_name}",
            "indexFilterable": True,
        },
        {
            "name": "file_id",
            "dataType": ["text"],
            "description": "Links to CaseDocuments.file_id",
            "indexFilterable": True,
        },
        {
            "name": "section_name",
            "dataType": ["text"],
            "description": "Section name (summary, facts, judgment, etc.)",
            "indexFilterable": True,
        },
        {
            "name": "sequence_number",
            "dataType": ["int"],
            "description": "Section sequence (1-9)",
        },
        {
            "name": "text",
            "dataType": ["text"],
            "description": "Section content text",
            "indexSearchable": True,
        },
    ],
}


# Collection 4: CaseChunks (markdown chunks with vectors)
CASE_CHUNKS_SCHEMA: Dict[str, Any] = {
    "class": "CaseChunks",
    "description": "Chunked markdown with embeddings",
    "vectorizer": "none",
    "vectorIndexConfig": {
        "distance": "cosine",
        "ef": -1,
        "efConstruction": 200,
        "maxConnections": 32,
    },
    "properties": [
        {
            "name": "chunk_id",
            "dataType": ["text"],
            "description": "Deterministic UUID: {file_id}::chunk::{chunk_index}",
            "indexFilterable": True,
        },
        {
            "name": "file_id",
            "dataType": ["text"],
            "description": "Links to CaseDocuments.file_id",
            "indexFilterable": True,
        },
        {
            "name": "chunk_index",
            "dataType": ["int"],
            "description": "0-based chunk sequence number",
        },
        {
            "name": "text",
            "dataType": ["text"],
            "description": "Chunk content text",
            "indexSearchable": True,
        },
        {
            "name": "token_count",
            "dataType": ["int"],
            "description": "Number of tokens in chunk",
        },
    ],
}


# All schemas for batch initialization
ALL_SCHEMAS: List[Dict[str, Any]] = [
    CASE_DOCUMENTS_SCHEMA,
    CASE_METADATA_SCHEMA,
    CASE_SECTIONS_SCHEMA,
    CASE_CHUNKS_SCHEMA,
]
