# CaseMind Entry Point Guide

## Main Entry Point

**`ingest_cli.py`** is the primary entry point for the Weaviate ingestion pipeline.

## Usage

### 1. Ingest Single File
```bash
python ingest_cli.py ingest --file cases/input_files/case1.pdf
```

### 2. Ingest Directory (Batch)
```bash
# All PDFs in directory
python ingest_cli.py ingest --directory cases/input_files

# Specific pattern
python ingest_cli.py ingest --directory cases/input_files --pattern "*.pdf"
```

### 3. Verify Ingestion
```bash
python ingest_cli.py verify --file-id <file_id_from_ingestion>
```

### 4. Search Sections
```bash
python ingest_cli.py search --query "what are the facts of the case" --limit 10
```

## Pipeline Flow

```
PDF/Markdown File
    ↓
[Stage 1: Markdown Extraction]
    ↓
[Stage 2: Content Hashing & Storage]
    ↓
[Stage 3: Text Chunking]
    ↓
[Stage 4a: summary_extraction]
    ├── Extract comprehensive summary from MARKDOWN
    ├── Format: main_template.json schema
    ├── Extracts: metadata, case_facts, evidence, arguments, reasoning, judgement
    └── Identifies: most_appropriate_section in metadata
    ↓
[Stage 4b: template_fact_extraction]
    ├── Extract template-specific facts from SUMMARY (NOT markdown)
    ├── Load template based on most_appropriate_section
    ├── Inputs: template_schema + case_facts + evidence + arguments + reasoning + judgement
    └── Extracts: tier_1_determinative, tier_2_material, tier_3_contextual, residual_details
    ↓
[Stage 5: Embedding Generation]
    ↓
[Stage 6: Weaviate Batch Upsert]
    ├── CaseDocuments (file metadata)
    ├── CaseMetadata (legal metadata)
    ├── CaseSections (structured sections with embeddings)
    └── CaseChunks (text chunks with embeddings)
    ↓
[Stage 7: Verification]
```

## Key Components

### Services
- **ExtractionService**: Two-stage LLM extraction
  - `summary_extraction(markdown_text)` → ComprehensiveExtraction
    - Extracts comprehensive summary from markdown using main_template.json schema
    - Returns: metadata (with most_appropriate_section), case_facts, evidence, arguments, reasoning, judgement
  - `template_fact_extraction(summary)` → Dict[str, Any]
    - Extracts template-specific facts from summary (NOT markdown)
    - Uses most_appropriate_section to load specific template
    - Returns: template_id, template_schema, extracted_facts (with tier structure)
  
- **ChunkingService**: Text chunking (512 tokens, 10% overlap)
- **EmbeddingService**: Generate 768-d vectors (all-mpnet-base-v2)
- **MarkdownService**: Normalize & store markdown
- **StorageAdapter**: Content-addressed local storage

### Infrastructure
- **WeaviateClient**: Weaviate 4.9+ connection management
- **WeaviateSchema**: Schema definitions for 4 collections

### Pipeline
- **WeaviateIngestionPipeline**: Orchestrates entire flow
  - `ingest_single(file_path)` → WeaviateIngestionResult
  - `ingest_batch(file_paths)` → List[WeaviateIngestionResult]
  - `verify_ingestion(file_id)` → Dict[str, int]

## Configuration

All configuration is in `.env`:
```env
WEAVIATE_URL=http://localhost:8080
WEAVIATE_API_KEY=
OPENAI_API_KEY=your_key_here
MARKDOWN_STORAGE_BASE=cases/local_storage_md
MAIN_TEMPLATE_PATH=templates/main_template.json
PROMPTS_PATH=prompts/prompts.json
```

## Testing

Run the test suite:
```bash
python test_weaviate_pipeline.py
```

## Helper Scripts

- **run_weaviate.bat** (Windows CMD)
- **run_weaviate.ps1** (PowerShell)

Both provide commands for:
- Starting Weaviate
- Initializing schema
- Running ingestion
- Running tests
- Verifying files

## Quick Start

1. **Start Weaviate**:
   ```bash
   docker-compose up -d
   ```

2. **Initialize Schema**:
   ```bash
   python src/scripts/init_weaviate.py
   ```

3. **Ingest Files**:
   ```bash
   python ingest_cli.py ingest --directory cases/input_files
   ```

4. **Verify**:
   ```bash
   python ingest_cli.py verify --file-id <file_id>
   ```

## Error Handling

The pipeline includes comprehensive error handling:
- **Duplicate detection**: Skips already-ingested files
- **Validation**: Checks for required fields
- **Logging**: Detailed logs for debugging
- **Result tracking**: Each ingestion returns status (success/skipped/error)

## Architecture Notes

- **Two-stage extraction**: Stage 4 has been split into:
  1. **summary_extraction**: Extracts comprehensive summary from markdown
  2. **template_fact_extraction**: Extracts template-specific facts from summary only
  
- **Deterministic UUIDs**: All IDs are UUID5-based for reproducibility

- **Content-addressed storage**: Markdown files stored by SHA-256 hash

- **Batch processing**: Optimized for multiple files with progress tracking
