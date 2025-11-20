# CaseMind - Final System Design Document

## Executive Summary
This document provides the complete architectural design for CaseMind, a legal case similarity search system built using Haystack, following SOLID principles and industry-standard design patterns.

## 1. ARCHITECTURE OVERVIEW

### 1.1 Layered Architecture
```
┌─────────────────────────────────────────────────────────────┐
│              Presentation Layer (CLI with Rich)             │
│                  src/presentation/                          │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│              Pipeline Orchestration Layer                    │
│         src/pipelines/ (Haystack Pipelines)                 │
│  - DataIngestionPipeline                                    │
│  - SimilaritySearchPipeline                                 │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                  Services Layer                             │
│              src/services/ (Business Logic)                 │
│  - PDFLoader, EmbeddingService                              │
│  - MetadataExtractor, FactExtractor                         │
│  - TemplateSelector, DuplicateChecker                       │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│            Infrastructure Layer                             │
│         src/infrastructure/ (External Systems)              │
│  - PGVectorDocumentStore (PostgreSQL + pgvector)            │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                  Core Layer                                 │
│          src/core/ (Interfaces, Models, Config)             │
│  - Interfaces (IDocumentLoader, IEmbedder, etc.)            │
│  - Models (DataClasses)                                     │
│  - Configuration (Singleton)                                │
│  - Exceptions                                               │
└─────────────────────────────────────────────────────────────┘
```

### 1.2 Design Patterns Applied

| Pattern | Location | Purpose |
|---------|----------|---------|
| **Singleton** | Config, DocumentStore | Single instance management |
| **Factory** | ModelManager | Model creation and caching |
| **Adapter** | PDFLoader, Service wrappers | Interface adaptation |
| **Strategy** | Embedding selection, Search modes | Algorithm selection |
| **Facade** | Pipeline classes | Simplify complex subsystems |
| **Dependency Injection** | All service constructors | Loose coupling |

### 1.3 SOLID Principles

#### Single Responsibility Principle (SRP)
- Each class has one reason to change
- PDFLoader: only loads PDFs
- EmbeddingService: only generates embeddings
- DocumentStore: only manages database operations

#### Open/Closed Principle (OCP)
- Extensible through interfaces
- New extractors can be added without modifying existing code
- New search strategies via Strategy pattern

#### Liskov Substitution Principle (LSP)
- All implementations honor interface contracts
- Any IDocumentLoader can replace another

#### Interface Segregation Principle (ISP)
- Small, focused interfaces
- IDocumentLoader, IEmbedder, IMetadataExtractor
- Clients depend only on methods they use

#### Dependency Inversion Principle (DIP)
- Depend on abstractions, not concretions
- Services depend on interfaces
- Implementations injected at runtime

## 2. COMPLETE CLASS DIAGRAM

```
┌──────────────────────────────────────────────────────────────────┐
│                         CORE LAYER                               │
└──────────────────────────────────────────────────────────────────┘

<<interface>> IDocumentLoader
  + load(file_path: Path) -> str
  + validate(file_path: Path) -> bool

<<interface>> IMetadataExtractor
  + extract(text: str, file_path: Path) -> Dict

<<interface>> ITemplateSelector
  + select(metadata: Dict) -> Template

<<interface>> IFactExtractor
  + extract(text: str, template: Template) -> Dict

<<interface>> IEmbedder
  + embed_text(text: str) -> ndarray
  + embed_batch(texts: List[str]) -> ndarray

<<interface>> IDocumentStore
  + write_document(document: Dict) -> str
  + query_by_embedding(embedding, top_k) -> List[Dict]
  + get_document_by_id(id: str) -> Dict
  + check_duplicate(file_hash: str) -> Dict

<<interface>> IDuplicateChecker
  + check(file_path: Path, metadata: Dict) -> DuplicateStatus

<<interface>> IResultFormatter
  + format_summary(metadata: Dict, facts: Dict)
  + format_similar_cases(results: List[Dict])

┌─────────────────────────────────┐
│ Config «Singleton»              │
├─────────────────────────────────┤
│ - _instance: Config             │
│ - db_connection_string: str     │
│ - embedding_model: str          │
│ - ranker_model: str             │
│ - top_k: int                    │
│ - threshold: float              │
├─────────────────────────────────┤
│ + __new__() -> Config           │
│ + get(key: str) -> Any          │
│ + to_dict() -> Dict             │
└─────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────┐
│                     MODELS (DataClasses)                         │
└──────────────────────────────────────────────────────────────────┘

@dataclass CaseMetadata
  - case_title: str
  - court_name: str
  - judgment_date: str
  - sections_invoked: List[str]
  - most_appropriate_section: str
  + to_dict() -> Dict

@dataclass Template
  - template_id: str
  - label: str
  - schema: Dict
  - confidence_score: float

@dataclass ExtractedFacts
  - tier_1_parties: Dict
  - tier_2_incident: Dict
  - tier_3_legal: Dict
  - tier_4_procedural: Dict
  + to_summary_text() -> str

@dataclass Document
  - id: str
  - content: str
  - meta: Dict
  - embedding_facts: ndarray
  - embedding_metadata: ndarray
  - file_hash: str
  - original_filename: str

@dataclass IngestResult
  - case_id: str
  - status: ProcessingStatus
  - metadata: CaseMetadata
  - facts_summary: str
  - embeddings: Dict[str, ndarray]

@dataclass SimilaritySearchResult
  - input_case: IngestResult
  - similar_cases: List[SimilarCase]
  - total_retrieved: int
  - total_above_threshold: int

┌──────────────────────────────────────────────────────────────────┐
│                   INFRASTRUCTURE LAYER                           │
└──────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────┐
│ PGVectorDocumentStore           │
│ implements IDocumentStore       │
│ «Singleton»                     │
├─────────────────────────────────┤
│ - connection: Connection        │
│ - config: Config                │
├─────────────────────────────────┤
│ + ensure_pgvector_extension()  │
│ + create_schema()               │
│ + write_document(doc) -> str    │
│ + query_by_embedding(...) -> []│
│ + get_document_by_id(...) -> {} │
│ + check_duplicate(...) -> {}    │
│ + get_statistics() -> Dict      │
└─────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────┐
│                      SERVICES LAYER                              │
└──────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────┐
│ PDFLoader                       │
│ implements IDocumentLoader      │
├─────────────────────────────────┤
│ + validate(path) -> bool        │
│ + load(path) -> str             │
│ - _clean_text(text) -> str      │
└─────────────────────────────────┘

┌─────────────────────────────────┐
│ EmbeddingService                │
│ implements IEmbedder            │
├─────────────────────────────────┤
│ - model: SentenceTransformer    │
│ - config: Config                │
├─────────────────────────────────┤
│ + embed_text(text) -> ndarray   │
│ + embed_batch(texts) -> ndarray │
│ + embed_facts(text) -> ndarray  │
│ + embed_metadata(meta) -> ndarr │
│ + embed_document_dual(...) -> {}│
└─────────────────────────────────┘

┌─────────────────────────────────┐
│ MetadataExtractor               │
│ implements IMetadataExtractor   │
├─────────────────────────────────┤
│ - llm_client: OpenAI            │
│ - prompt_template: str          │
├─────────────────────────────────┤
│ + extract(text, path) -> Dict   │
│ - _build_prompt(text) -> str    │
│ - _parse_response(resp) -> Dict │
└─────────────────────────────────┘

┌─────────────────────────────────┐
│ TemplateSelector                │
│ implements ITemplateSelector    │
├─────────────────────────────────┤
│ - ontology_matcher: Ontology    │
│ - template_loader: Loader       │
├─────────────────────────────────┤
│ + select(metadata) -> Template  │
│ - _match_sections(meta) -> str  │
└─────────────────────────────────┘

┌─────────────────────────────────┐
│ FactExtractor                   │
│ implements IFactExtractor       │
├─────────────────────────────────┤
│ - llm_client: OpenAI            │
├─────────────────────────────────┤
│ + extract(text, template) -> {} │
│ - _build_prompt(...) -> str     │
│ - _parse_response(...) -> Dict  │
└─────────────────────────────────┘

┌─────────────────────────────────┐
│ DuplicateChecker                │
│ implements IDuplicateChecker    │
├─────────────────────────────────┤
│ - store: IDocumentStore         │
├─────────────────────────────────┤
│ + check(path, meta) -> Status   │
│ - compute_file_hash(path) -> str│
│ - fuzzy_match_title(...) -> {}  │
└─────────────────────────────────┘

┌─────────────────────────────────┐
│ RichFormatter                   │
│ implements IResultFormatter     │
├─────────────────────────────────┤
│ - console: rich.Console         │
├─────────────────────────────────┤
│ + format_summary(meta, facts)   │
│ + format_similar_cases(results) │
│ + display_progress(...)         │
│ + display_welcome()             │
│ + display_health_status(...)    │
└─────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────┐
│                     PIPELINE LAYER                               │
└──────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│ DataIngestionPipeline                   │
│ «Facade» «Pipeline»                     │
├─────────────────────────────────────────┤
│ - pdf_loader: IDocumentLoader           │
│ - metadata_extractor: IMetadataExtractor│
│ - template_selector: ITemplateSelector  │
│ - fact_extractor: IFactExtractor        │
│ - embedder: IEmbedder                   │
│ - store: IDocumentStore                 │
│ - duplicate_checker: IDuplicateChecker  │
├─────────────────────────────────────────┤
│ + ingest_single(path) -> IngestResult   │
│ + process_batch(folder) -> BatchResult  │
│ - _process_file(path) -> IngestResult   │
└─────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│ SimilaritySearchPipeline                │
│ «Facade» «Pipeline»                     │
├─────────────────────────────────────────┤
│ - ingestion: DataIngestionPipeline      │
│ - store: IDocumentStore                 │
│ - embedder: IEmbedder                   │
│ - ranker: CrossEncoder                  │
│ - config: Config                        │
├─────────────────────────────────────────┤
│ + run_full_pipeline(path) -> Result     │
│ + retrieve_similar(emb, k) -> List      │
│ + rerank_results(q, docs) -> List       │
│ + filter_by_threshold(docs) -> List     │
│ - _exclude_duplicates(docs) -> List     │
└─────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────┐
│                    PRESENTATION LAYER                            │
└──────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│ CLIApp                                  │
│ «Main Controller»                       │
├─────────────────────────────────────────┤
│ - ingestion_pipeline: DataIngestion     │
│ - similarity_pipeline: SimilaritySearch │
│ - formatter: IResultFormatter           │
│ - store: IDocumentStore                 │
├─────────────────────────────────────────┤
│ + start()                               │
│ + display_menu()                        │
│ + ingest_cases_batch(folder)            │
│ + find_similar_cases(file)              │
│ + show_statistics()                     │
│ + health_check()                        │
│ + shutdown()                            │
└─────────────────────────────────────────┘
```

## 3. DATABASE DESIGN

### 3.1 Schema

```sql
CREATE TABLE haystack_documents (
    id                      VARCHAR(255) PRIMARY KEY,
    content                 TEXT NOT NULL,
    content_type            VARCHAR(50) DEFAULT 'text',
    meta                    JSONB NOT NULL,
    embedding_facts         vector(768) NOT NULL,
    embedding_metadata      vector(768) NOT NULL,
    score                   FLOAT,
    file_hash               VARCHAR(64) UNIQUE NOT NULL,
    original_filename       VARCHAR(512),
    created_at              TIMESTAMP DEFAULT NOW(),
    updated_at              TIMESTAMP DEFAULT NOW()
);
```

### 3.2 Indexes

```sql
-- Vector similarity indexes
CREATE INDEX idx_embedding_facts_ivfflat 
ON haystack_documents USING ivfflat (embedding_facts vector_cosine_ops) WITH (lists = 100);

CREATE INDEX idx_embedding_metadata_ivfflat 
ON haystack_documents USING ivfflat (embedding_metadata vector_cosine_ops) WITH (lists = 100);

-- Metadata indexes
CREATE INDEX idx_meta_gin ON haystack_documents USING gin (meta);
CREATE INDEX idx_case_id ON haystack_documents ((meta->>'case_id'));
CREATE INDEX idx_file_hash ON haystack_documents (file_hash);
CREATE INDEX idx_template_id ON haystack_documents ((meta->>'template_id'));
CREATE INDEX idx_case_title ON haystack_documents ((meta->>'case_title'));
```

## 4. DETAILED WORKFLOWS

### 4.1 Batch Ingestion Flow

```
[User selects "Ingest Cases Batch"]
    ↓
[Enter folder path]
    ↓
[CLIApp.ingest_cases_batch(folder_path)]
    ↓
[DataIngestionPipeline.process_batch(folder_path)]
    ↓
[Scan folder for PDFs] ────→ [List of PDF files]
    ↓
[FOR EACH PDF file]:
    ├─→ [DuplicateChecker.check(file_path)]
    │       ↓
    │   [Is Duplicate?] ──YES──→ [Skip, log as duplicate]
    │       │ NO
    │       ↓
    ├─→ [PDFLoader.load(file_path)] ────→ [raw_text]
    │       ↓
    ├─→ [MetadataExtractor.extract(raw_text)] ────→ [metadata]
    │       ↓
    ├─→ [TemplateSelector.select(metadata)] ────→ [template]
    │       ↓
    ├─→ [FactExtractor.extract(raw_text, template)] ────→ [facts]
    │       ↓
    ├─→ [facts.to_summary_text()] ────→ [facts_text]
    │       ↓
    ├─→ [EmbeddingService.embed_document_dual(facts_text, metadata)]
    │       ↓────→ [embedding_facts, embedding_metadata]
    │       ↓
    ├─→ [Create Document object]
    │       ↓
    ├─→ [DocumentStore.write_document(document)] ────→ [document_id]
    │       ↓
    └─→ [Update progress, log success]
        ↓
[Display batch summary]
    - Total: N
    - Processed: X
    - Duplicates: Y
    - Failed: Z
```

### 4.2 Similarity Search Flow

```
[User selects "Find Similar Cases"]
    ↓
[Enter file path]
    ↓
[CLIApp.find_similar_cases(file_path)]
    ↓
[SimilaritySearchPipeline.run_full_pipeline(file_path)]
    ↓
┌─────────────────────────────────────────┐
│ PHASE 1: INGEST INPUT CASE             │
├─────────────────────────────────────────┤
│ [DuplicateChecker.check(file_path)]    │
│     ↓ NOT DUPLICATE                    │
│ [DataIngestionPipeline.ingest_single()]│
│     ↓                                  │
│ [Extract metadata, facts, embeddings]  │
│     ↓                                  │
│ [Store in database]                    │
│     ↓                                  │
│ [Display input case summary]           │
└─────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────┐
│ PHASE 2: RETRIEVE SIMILAR CASES        │
├─────────────────────────────────────────┤
│ [DocumentStore.query_by_embedding()]   │
│   - Use embedding_facts                │
│   - Top K = 3                          │
│   - Exclude input case ID              │
│   - Exclude similarity >= 0.99         │
│     ↓                                  │
│ [Retrieved candidates: List[Document]] │
└─────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────┐
│ PHASE 3: RE-RANK WITH CROSS-ENCODER    │
├─────────────────────────────────────────┤
│ [For each candidate]:                  │
│   - Prepare (query_text, doc_text)    │
│   - CrossEncoder.predict(pairs)        │
│   - Assign cross_encoder_score         │
│     ↓                                  │
│ [Sort by cross_encoder_score DESC]     │
└─────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────┐
│ PHASE 4: FILTER BY THRESHOLD           │
├─────────────────────────────────────────┤
│ [Keep only: cross_encoder_score > 0.0] │
│     ↓                                  │
│ [Filtered results: List[SimilarCase]]  │
└─────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────┐
│ PHASE 5: DISPLAY RESULTS               │
├─────────────────────────────────────────┤
│ [RichFormatter.format_similar_cases()] │
│   - Case title                         │
│   - Court, date                        │
│   - Cosine similarity score            │
│   - Cross-encoder score                │
│   - Facts summary (truncated)          │
└─────────────────────────────────────────┘
```

## 5. FILE STRUCTURE

```
src/
├── __init__.py
├── main.py                          # Application entry point
│
├── core/                            # Core abstractions
│   ├── __init__.py
│   ├── config.py                    # Singleton configuration
│   ├── exceptions.py                # Custom exceptions
│   ├── interfaces.py                # Abstract base classes (ABCs)
│   └── models.py                    # Data models (dataclasses)
│
├── infrastructure/                  # External integrations
│   ├── __init__.py
│   └── document_store.py            # PostgreSQL + pgvector
│
├── services/                        # Business logic services
│   ├── __init__.py
│   ├── pdf_loader.py                # PDF loading (PyMuPDF)
│   ├── embedding_service.py         # Dual embeddings
│   ├── metadata_extractor.py        # LLM metadata extraction
│   ├── template_selector.py         # Template matching
│   ├── fact_extractor.py            # LLM fact extraction
│   └── duplicate_checker.py         # Duplicate detection
│
├── pipelines/                       # Pipeline orchestrators
│   ├── __init__.py
│   ├── ingestion_pipeline.py        # Data ingestion pipeline
│   └── similarity_pipeline.py       # Similarity search pipeline
│
├── presentation/                    # UI layer
│   ├── __init__.py
│   ├── cli_app.py                   # CLI application controller
│   └── formatters.py                # Rich UI formatters
│
├── utils/                           # Utilities
│   ├── __init__.py
│   └── helpers.py                   # Helper functions
│
└── scripts/                         # Utility scripts
    ├── __init__.py
    └── init_database.py             # Database initialization
```

## 6. KEY DESIGN DECISIONS

### 6.1 Why Dual Embeddings?
- **Facts embedding**: Captures semantic similarity of case circumstances
- **Metadata embedding**: Enables entity-based retrieval (names, courts, sections)
- **Future-proof**: Supports hybrid search and natural language queries
- **Minimal overhead**: 6KB per case vs 3KB (100% increase, but only ~60MB for 10K cases)

### 6.2 Why Haystack?
- Industry-standard pipeline framework
- Built-in support for embeddings, retrievers, rankers
- Extensible with custom nodes
- Active community and ecosystem

### 6.3 Why PostgreSQL + pgvector?
- ACID compliance for legal data
- Mature, reliable database
- pgvector provides efficient vector search
- JSON support for flexible metadata
- No vendor lock-in

### 6.4 Why Singleton for Config/Store?
- Single source of truth for configuration
- Single database connection (connection pooling can be added later)
- Thread-safe access
- Lazy initialization

### 6.5 Why Interface Segregation?
- Clients depend only on methods they use
- Easier testing (mock individual interfaces)
- Better modularity
- Clear contracts

## 7. EXTENSIBILITY POINTS

### 7.1 Adding New Document Loaders
```python
class WordDocLoader(IDocumentLoader):
    def load(self, file_path: Path) -> str:
        # Implementation for Word docs
        pass
```

### 7.2 Adding New Embedding Models
```python
# Just change config
EMBEDDING_MODEL=openai/text-embedding-3-large
```

### 7.3 Adding New Search Strategies
```python
class HybridSearchStrategy:
    def search(self, facts_emb, meta_emb, alpha=0.7):
        # Weighted combination
        pass
```

### 7.4 Adding New Output Formats
```python
class JSONFormatter(IResultFormatter):
    def format_similar_cases(self, results):
        return json.dumps(results)
```

## 8. TESTING STRATEGY

### 8.1 Unit Tests
- Test each service in isolation
- Mock dependencies (interfaces)
- Cover edge cases and error paths

### 8.2 Integration Tests
- Test database operations
- Test LLM integrations
- Test pipeline flows

### 8.3 End-to-End Tests
- Upload sample PDF
- Verify ingestion
- Verify search results

## 9. PERFORMANCE CONSIDERATIONS

### 9.1 Database Optimization
- IVFFlat indexes for <100K docs
- HNSW indexes for >100K docs
- Tune lists parameter based on dataset size

### 9.2 Batch Processing
- Process PDFs in parallel (future enhancement)
- Batch embedding generation
- Transaction batching for writes

### 9.3 Model Loading
- Cache models in memory
- Lazy loading for optional components
- GPU support for faster embeddings

## 10. SECURITY CONSIDERATIONS

- Store API keys in environment variables
- Validate all user inputs
- Sanitize file paths
- Use prepared statements for SQL
- Hash file contents for duplicate detection
- No PII in logs

---

**Document Version**: 1.0  
**Last Updated**: 2024-11-19  
**Status**: Ready for Implementation
