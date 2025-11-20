"""
Data models and domain entities using dataclasses.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from datetime import datetime
from enum import Enum
import numpy as np


class ProcessingStatus(Enum):
    """Status of document processing."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED_DUPLICATE = "skipped_duplicate"


class MatchMethod(Enum):
    """Method used for duplicate detection."""
    FILE_HASH = "file_hash"
    CASE_ID = "case_id"
    TITLE_FUZZY = "title_fuzzy"
    NEW = "new"


@dataclass
class CaseMetadata:
    """Metadata extracted from legal case."""
    case_title: str
    court_name: str
    judgment_date: str
    sections_invoked: List[str]
    most_appropriate_section: str
    case_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'case_title': self.case_title,
            'court_name': self.court_name,
            'judgment_date': self.judgment_date,
            'sections_invoked': self.sections_invoked,
            'most_appropriate_section': self.most_appropriate_section,
            'case_id': self.case_id,
        }


@dataclass
class Template:
    """Template for fact extraction."""
    template_id: str
    label: str
    schema: Dict[str, Any]
    confidence_score: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'template_id': self.template_id,
            'label': self.label,
            'schema': self.schema,
            'confidence_score': self.confidence_score,
        }


@dataclass
class ExtractedFacts:
    """Structured facts extracted from case."""
    tier_1_parties: Dict[str, Any]
    tier_2_incident: Dict[str, Any]
    tier_3_legal: Dict[str, Any]
    tier_4_procedural: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'tier_1_parties': self.tier_1_parties,
            'tier_2_incident': self.tier_2_incident,
            'tier_3_legal': self.tier_3_legal,
            'tier_4_procedural': self.tier_4_procedural,
        }
    
    def to_summary_text(self) -> str:
        """Convert facts to concatenated summary text."""
        def extract_values(obj: Any) -> List[str]:
            """Recursively extract string values."""
            values = []
            if isinstance(obj, dict):
                for v in obj.values():
                    values.extend(extract_values(v))
            elif isinstance(obj, list):
                for item in obj:
                    values.extend(extract_values(item))
            elif isinstance(obj, str) and obj.strip():
                values.append(obj.strip())
            return values
        
        all_values = extract_values(self.to_dict())
        return ". ".join(all_values) + "." if all_values else ""


@dataclass
class DuplicateStatus:
    """Result of duplicate checking."""
    is_duplicate: bool
    existing_case_id: Optional[str] = None
    match_method: MatchMethod = MatchMethod.NEW
    similarity_score: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'is_duplicate': self.is_duplicate,
            'existing_case_id': self.existing_case_id,
            'match_method': self.match_method.value,
            'similarity_score': self.similarity_score,
        }


@dataclass
class Document:
    """Legal case document with embeddings."""
    id: str
    content: str
    meta: Dict[str, Any]
    embedding_facts: np.ndarray
    embedding_metadata: np.ndarray
    file_hash: str
    original_filename: str
    created_at: datetime = field(default_factory=datetime.now)
    score: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary (excluding embeddings)."""
        return {
            'id': self.id,
            'content': self.content,
            'meta': self.meta,
            'file_hash': self.file_hash,
            'original_filename': self.original_filename,
            'created_at': self.created_at.isoformat(),
            'score': self.score,
        }


@dataclass
class IngestResult:
    """Result of single file ingestion."""
    case_id: str
    document_id: str
    status: ProcessingStatus
    metadata: CaseMetadata
    facts_summary: str
    embedding_facts: np.ndarray
    embedding_metadata: np.ndarray
    error_message: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary (excluding embeddings)."""
        return {
            'case_id': self.case_id,
            'document_id': self.document_id,
            'status': self.status.value,
            'metadata': self.metadata.to_dict(),
            'facts_summary': self.facts_summary,
            'error_message': self.error_message,
        }


@dataclass
class BatchIngestResult:
    """Result of batch folder processing."""
    total_files: int
    processed: int
    skipped_duplicates: int
    failed: int
    case_ids: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'total_files': self.total_files,
            'processed': self.processed,
            'skipped_duplicates': self.skipped_duplicates,
            'failed': self.failed,
            'case_ids': self.case_ids,
            'errors': self.errors,
        }


@dataclass
class SimilarCase:
    """Similar case with scores."""
    document_id: str
    case_title: str
    court_name: str
    judgment_date: str
    facts_summary: str
    cosine_similarity: float
    cross_encoder_score: float
    sections_invoked: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'document_id': self.document_id,
            'case_title': self.case_title,
            'court_name': self.court_name,
            'judgment_date': self.judgment_date,
            'facts_summary': self.facts_summary,
            'cosine_similarity': self.cosine_similarity,
            'cross_encoder_score': self.cross_encoder_score,
            'sections_invoked': self.sections_invoked,
        }


@dataclass
class SimilaritySearchResult:
    """Result of similarity search pipeline."""
    input_case: IngestResult
    similar_cases: List[SimilarCase]
    total_retrieved: int
    total_above_threshold: int
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'input_case': self.input_case.to_dict(),
            'similar_cases': [case.to_dict() for case in self.similar_cases],
            'total_retrieved': self.total_retrieved,
            'total_above_threshold': self.total_above_threshold,
        }
