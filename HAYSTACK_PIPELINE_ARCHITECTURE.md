# Haystack Pipeline Architecture

## Overview
The CaseMind ingestion pipeline has been refactored to use **Haystack 2.x** framework with custom components. The pipeline maintains all 7 original processing stages while leveraging Haystack's declarative pipeline API.

## Pipeline Flow

```
PDF File(s)
    ↓
[1] PDFToMarkdownConverter
    ↓ (documents)
[2] MarkdownNormalizer
    ↓ (documents)
[3] TextChunker
    ↓ (documents, chunks)
[4a] SummaryExtractor
    ↓ (documents, chunks, extractions)
[4b] TemplateFactsExtractor
    ↓ (documents, chunks, extractions, sections)
[5] EmbeddingGenerator
    ↓ (documents, chunks, extractions, sections + vectors)
[6] WeaviateWriter
    ↓
Results (4 Weaviate collections populated)
```

## Custom Components

### 1. PDFToMarkdownConverter (`src/components/pdf_to_markdown.py`)
**Stage 1: PDF Extraction**
- **Input**: `file_paths: List[Path]`
- **Output**: `documents: List[Document]` (Haystack Documents with markdown content)
- **Logic**: Uses `PDFExtractionService` with PyMuPDF4LLM + Gemini Vision fallback

### 2. MarkdownNormalizer (`src/components/markdown_normalizer.py`)
**Stage 2: Markdown Normalization & Storage**
- **Input**: `documents: List[Document]`
- **Output**: `documents: List[Document]` (with `md_hash`, `md_uri`, `file_id` in meta)
- **Logic**: 
  - Normalizes markdown (deterministic whitespace)
  - Computes SHA-256 hash
  - Stores in content-addressed storage
  - Generates deterministic `file_id` from hash using UUID5

### 3. TextChunker (`src/components/text_chunker.py`)
**Stage 3: Text Chunking**
- **Input**: `documents: List[Document]`
- **Output**: 
  - `documents: List[Document]` (unchanged)
  - `chunks: List[Dict]` (chunk_index, text, token_count, file_id)
- **Logic**: Uses `ChunkingService` with RecursiveDocumentSplitter (512 tokens, 10% overlap)

### 4a. SummaryExtractor (`src/components/summary_extractor.py`)
**Stage 4a: Comprehensive Summary Extraction**
- **Input**: 
  - `documents: List[Document]`
  - `chunks: List[Dict]`
- **Output**: 
  - `documents: List[Document]` (with extraction added to meta)
  - `chunks: List[Dict]` (unchanged)
  - `extractions: List[Dict]` (ComprehensiveExtraction as dict)
- **Logic**: 
  - Calls OpenAI GPT-4 with `main_template.json` schema
  - Extracts: metadata, case_facts, evidence, arguments, reasoning, judgement
  - Identifies `most_appropriate_section` for template matching

### 4b. TemplateFactsExtractor (`src/components/template_facts_extractor.py`)
**Stage 4b: Template-Specific Fact Extraction**
- **Input**: 
  - `documents: List[Document]`
  - `chunks: List[Dict]`
  - `extractions: List[Dict]`
- **Output**: 
  - `documents: List[Document]` (with template_facts added to meta)
  - `chunks: List[Dict]` (unchanged)
  - `extractions: List[Dict]` (unchanged)
  - `sections: List[Dict]` (case sections + template facts section)
- **Logic**: 
  - Uses `most_appropriate_section` to load specific template (e.g., IPC 302, IPC 498A)
  - Extracts template-specific facts from summary (NOT markdown)
  - Creates sections from extraction (Case Facts, Evidence, Arguments, Reasoning, Judgement, Template Facts)

### 5. EmbeddingGenerator (`src/components/embedding_generator.py`)
**Stage 5: Batch Embedding Generation**
- **Input**: 
  - `documents: List[Document]`
  - `chunks: List[Dict]`
  - `extractions: List[Dict]`
  - `sections: List[Dict]`
- **Output**: Same inputs with `vector` field added to chunks and sections
- **Logic**: 
  - Uses `EmbeddingService` (SentenceTransformer: all-mpnet-base-v2)
  - Generates 768-d embeddings
  - L2-normalizes for cosine similarity

### 6. WeaviateWriter (`src/components/weaviate_writer.py`)
**Stage 6: Weaviate Batch Upsert**
- **Input**: 
  - `documents: List[Document]`
  - `chunks: List[Dict]`
  - `extractions: List[Dict]`
  - `sections: List[Dict]`
- **Output**: `results: List[Dict]` (ingestion results per document)
- **Logic**: 
  - Writes to 4 Weaviate collections:
    1. **CaseDocuments**: file_id, md_hash, original_filename, created_at
    2. **CaseMetadata**: case_number, case_title, court_name, judges, sections_invoked, etc.
    3. **CaseSections**: section_id, section_name, text, vector (768-d)
    4. **CaseChunks**: chunk_id, chunk_index, text, token_count, vector (768-d)
  - Generates deterministic UUIDs (UUID5) for all entities
  - Supports duplicate detection via `skip_existing` flag

## Pipeline Initialization

```python
from src.pipelines.weaviate_ingestion_pipeline import WeaviateIngestionPipeline

# Initialize pipeline
pipeline = WeaviateIngestionPipeline()

# Ingest single file
result = pipeline.ingest_single("path/to/case.pdf")

# Ingest batch
results = pipeline.ingest_batch([Path("case1.pdf"), Path("case2.pdf")])

# Verify ingestion
counts = pipeline.verify_ingestion(file_id)
```

## Key Features

### 1. Declarative Pipeline Definition
```python
pipeline = Pipeline()
pipeline.add_component("pdf_converter", PDFToMarkdownConverter())
pipeline.add_component("markdown_normalizer", MarkdownNormalizer())
# ... add all components

# Connect components
pipeline.connect("pdf_converter.documents", "markdown_normalizer.documents")
pipeline.connect("markdown_normalizer.documents", "text_chunker.documents")
# ... connect all components
```

### 2. Batch Processing
- Single `pipeline.run()` call processes all files
- Haystack handles parallelization and batching internally

### 3. Deterministic UUIDs
- All entity IDs (file_id, section_id, chunk_id, metadata_id) are deterministic
- Same content always produces same IDs (idempotent ingestion)
- Uses UUID5 namespace-based generation

### 4. Error Handling
- Each component handles errors gracefully
- Error documents passed through pipeline with `error` in meta
- Final results include status: "success" | "skipped" | "error"

### 5. Backward Compatibility
- `ingest_single()` and `ingest_batch()` methods maintained
- Same return types (`WeaviateIngestionResult`)
- Existing CLI (`ingest_cli.py`) works unchanged

## File Structure

```
src/
├── components/              # NEW: Custom Haystack components
│   ├── __init__.py
│   ├── pdf_to_markdown.py
│   ├── markdown_normalizer.py
│   ├── text_chunker.py
│   ├── summary_extractor.py
│   ├── template_facts_extractor.py
│   ├── embedding_generator.py
│   └── weaviate_writer.py
├── pipelines/
│   └── weaviate_ingestion_pipeline.py  # REFACTORED: Haystack Pipeline wrapper
├── services/                # UNCHANGED: Service layer (wrapped by components)
│   ├── pdf_extraction_service.py
│   ├── markdown_service.py
│   ├── chunking_service.py
│   ├── extraction_service.py
│   └── embedding_service.py
├── core/
│   ├── config.py
│   └── models.py
└── infrastructure/
    ├── weaviate_client.py
    └── storage_adapter.py
```

## Benefits of Haystack Architecture

1. **Modularity**: Each stage is a self-contained component
2. **Testability**: Components can be tested independently
3. **Extensibility**: Easy to add new components or replace existing ones
4. **Observability**: Haystack provides built-in logging and metrics
5. **Type Safety**: Input/output types enforced at component boundaries
6. **Scalability**: Haystack handles batching and parallelization

## Migration Notes

- **No changes** to service layer (`src/services/`)
- **No changes** to data models (`src/core/models.py`)
- **No changes** to infrastructure (`src/infrastructure/`)
- **New** component layer wraps existing services
- **Refactored** pipeline uses Haystack's declarative API
- **Maintained** backward compatibility with CLI and existing code

## Testing

```bash
# Test pipeline initialization
python -c "from src.pipelines.weaviate_ingestion_pipeline import WeaviateIngestionPipeline; p = WeaviateIngestionPipeline(); print('✓ Pipeline initialized with', len(p.pipeline.graph.nodes), 'components')"

# Test single file ingestion
python ingest_cli.py ingest --file "cases/test_ingest/case.pdf"

# Test batch ingestion
python ingest_cli.py batch --folder "cases/input_files/"
```

## Next Steps

1. Add Haystack's built-in caching for expensive operations (LLM calls, embeddings)
2. Implement Haystack's evaluation framework for quality metrics
3. Add Haystack's streaming support for real-time ingestion
4. Integrate Haystack's observability tools (Prometheus, Grafana)
