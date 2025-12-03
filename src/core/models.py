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
        return " ".join(all_values) + " " if all_values else ""


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
    embedding_facts: Optional[np.ndarray] = None
    embedding_metadata: Optional[np.ndarray] = None
    # Additional embeddings for in-memory search (when store_in_db=False)
    embedding_case_facts: Optional[np.ndarray] = None
    embedding_issues: Optional[np.ndarray] = None
    embedding_evidence: Optional[np.ndarray] = None
    embedding_arguments: Optional[np.ndarray] = None
    embedding_reasoning: Optional[np.ndarray] = None
    embedding_judgement: Optional[np.ndarray] = None
    error_message: Optional[str] = None
    file_hash: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary (excluding embeddings)."""
        return {
            'case_id': self.case_id,
            'document_id': self.document_id,
            'status': self.status.value,
            'metadata': self.metadata.to_dict() if self.metadata else {},
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
    query_file: str
    input_case: Optional[IngestResult]
    similar_cases: List[SimilarCase]
    total_above_threshold: int
    search_mode: str = "facts"
    total_retrieved: int = 0
    error_message: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'query_file': self.query_file,
            'input_case': self.input_case.to_dict() if self.input_case else None,
            'similar_cases': [case.to_dict() for case in self.similar_cases],
            'total_retrieved': self.total_retrieved,
            'total_above_threshold': self.total_above_threshold,
            'search_mode': self.search_mode,
            'error_message': self.error_message,
        }


# ============================================================================
# Weaviate Ingestion Models
# ============================================================================


@dataclass
class TextChunk:
    """Text chunk with metadata for Weaviate ingestion."""
    chunk_index: int
    text: str
    token_count: int
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'chunk_index': self.chunk_index,
            'text': self.text,
            'token_count': self.token_count,
        }


@dataclass
class CaseSection:
    """Case section with text and optional vector."""
    section_name: str
    sequence_number: int
    text: str
    vector: Optional[List[float]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary (excluding vector)."""
        return {
            'section_name': self.section_name,
            'sequence_number': self.sequence_number,
            'text': self.text,
        }


@dataclass
class LowerCourtHistory:
    """Lower court verdicts."""
    trial_court_verdict: str = ""
    high_court_verdict: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'trial_court_verdict': self.trial_court_verdict,
            'high_court_verdict': self.high_court_verdict,
        }


@dataclass
class WitnessTestimony:
    """Witness testimony details."""
    witness_id: str
    name: str
    role: str
    summary: str
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'witness_id': self.witness_id,
            'name': self.name,
            'role': self.role,
            'summary': self.summary,
        }


@dataclass
class WeaviateMetadata:
    """Enhanced legal metadata for Weaviate - comprehensive schema."""
    # Basic metadata
    case_number: Optional[str] = None
    case_title: Optional[str] = None
    court_name: Optional[str] = None
    judgment_date: Optional[str] = None
    appellant_or_petitioner: Optional[str] = None
    respondent: Optional[str] = None
    judges_coram: List[str] = field(default_factory=list)
    counsel_for_appellant: Optional[str] = None
    counsel_for_respondent: Optional[str] = None
    sections_invoked: List[str] = field(default_factory=list)
    most_appropriate_section: Optional[str] = None
    case_type: Optional[str] = None
    citation: Optional[str] = None
    acts_and_sections: Optional[str] = None
    lower_court_history: Optional[LowerCourtHistory] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'case_number': self.case_number,
            'case_title': self.case_title,
            'court_name': self.court_name,
            'judgment_date': self.judgment_date,
            'appellant_or_petitioner': self.appellant_or_petitioner,
            'respondent': self.respondent,
            'judges_coram': self.judges_coram,
            'counsel_for_appellant': self.counsel_for_appellant,
            'counsel_for_respondent': self.counsel_for_respondent,
            'sections_invoked': self.sections_invoked,
            'most_appropriate_section': self.most_appropriate_section,
            'case_type': self.case_type,
            'citation': self.citation,
            'acts_and_sections': self.acts_and_sections,
            'lower_court_history': self.lower_court_history.to_dict() if self.lower_court_history else None,
        }


@dataclass
class CaseFacts:
    """Case facts structure."""
    prosecution_version: str = ""
    defence_version: str = ""
    timeline_of_events: List[str] = field(default_factory=list)
    incident_location: str = ""
    motive_alleged: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'prosecution_version': self.prosecution_version,
            'defence_version': self.defence_version,
            'timeline_of_events': self.timeline_of_events,
            'incident_location': self.incident_location,
            'motive_alleged': self.motive_alleged,
        }


@dataclass
class Evidence:
    """Evidence structure."""
    witness_testimonies: List[WitnessTestimony] = field(default_factory=list)
    medical_evidence: str = ""
    forensic_evidence: str = ""
    documentary_evidence: List[str] = field(default_factory=list)
    recovery_and_seizure: str = ""
    expert_opinions: str = ""
    investigation_findings: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'witness_testimonies': [w.to_dict() for w in self.witness_testimonies],
            'medical_evidence': self.medical_evidence,
            'forensic_evidence': self.forensic_evidence,
            'documentary_evidence': self.documentary_evidence,
            'recovery_and_seizure': self.recovery_and_seizure,
            'expert_opinions': self.expert_opinions,
            'investigation_findings': self.investigation_findings,
        }


@dataclass
class Arguments:
    """Arguments by prosecution and defence."""
    prosecution: str = ""
    defence: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'prosecution': self.prosecution,
            'defence': self.defence,
        }


@dataclass
class Reasoning:
    """Court reasoning structure."""
    analysis_of_evidence: str = ""
    credibility_assessment: str = ""
    legal_principles_applied: str = ""
    circumstantial_chain: str = ""
    court_findings: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'analysis_of_evidence': self.analysis_of_evidence,
            'credibility_assessment': self.credibility_assessment,
            'legal_principles_applied': self.legal_principles_applied,
            'circumstantial_chain': self.circumstantial_chain,
            'court_findings': self.court_findings,
        }


@dataclass
class Judgement:
    """Final judgement structure."""
    final_decision: str = ""
    sentence_or_bail_conditions: str = ""
    directions: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'final_decision': self.final_decision,
            'sentence_or_bail_conditions': self.sentence_or_bail_conditions,
            'directions': self.directions,
        }


@dataclass
class ComprehensiveExtraction:
    """Complete extraction result with all structured data."""
    metadata: WeaviateMetadata
    case_facts: CaseFacts
    issues_for_determination: List[str] = field(default_factory=list)
    evidence: Optional[Evidence] = None
    arguments: Optional[Arguments] = None
    reasoning: Optional[Reasoning] = None
    judgement: Optional[Judgement] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'metadata': self.metadata.to_dict(),
            'case_facts': self.case_facts.to_dict(),
            'issues_for_determination': self.issues_for_determination,
            'evidence': self.evidence.to_dict() if self.evidence else {},
            'arguments': self.arguments.to_dict() if self.arguments else {},
            'reasoning': self.reasoning.to_dict() if self.reasoning else {},
            'judgement': self.judgement.to_dict() if self.judgement else {},
        }


@dataclass
class WeaviateIngestionResult:
    """Result of Weaviate ingestion for a single document."""
    file_id: str
    md_hash: str
    status: str  # "success", "skipped", "error"
    message: Optional[str] = None
    metadata: Optional[ComprehensiveExtraction] = None
    sections_count: int = 0
    chunks_count: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'file_id': self.file_id,
            'md_hash': self.md_hash,
            'status': self.status,
            'message': self.message,
            'metadata': self.metadata.to_dict() if self.metadata else {},
            'sections_count': self.sections_count,
            'chunks_count': self.chunks_count,
        }
