# Weaviate Ingestion Pipeline - Quick Start Guide

## Overview

The CaseMind Weaviate ingestion pipeline processes legal case documents (PDF/Markdown) and stores them in a structured vector database for semantic search and retrieval.

## Architecture

### Collections (4 total)

1. **CaseDocuments**: File metadata and storage URIs
2. **CaseMetadata**: Legal metadata (case number, court, judges, etc.)
3. **CaseSections**: 9 extracted sections with embeddings
4. **CaseChunks**: Text chunks with embeddings for fine-grained retrieval

### Pipeline Stages

1. **PDF → Markdown**: Extract text content
2. **Normalize & Store**: Content-addressed storage (SHA-256 hash)
3. **Chunking**: 512 tokens, 10% overlap
4. **Extraction**: LLM extracts 9 sections + metadata
5. **Embedding**: Generate 768-d vectors (L2 normalized)
6. **Weaviate Upsert**: Batch insert to 4 collections
7. **Verification**: Validate ingestion

## Prerequisites

### 1. Install Weaviate (Docker)

```powershell
docker pull semitechnologies/weaviate:latest

docker run -d `
  --name weaviate `
  -p 8080:8080 `
  -p 50051:50051 `
  -e AUTHENTICATION_ANONYMOUS_ACCESS_ENABLED=true `
  -e PERSISTENCE_DATA_PATH=/var/lib/weaviate `
  -e DEFAULT_VECTORIZER_MODULE=none `
  -e ENABLE_MODULES=text2vec-openai `
  -e CLUSTER_HOSTNAME=node1 `
  semitechnologies/weaviate:latest
```

Verify Weaviate is running:
```powershell
curl http://localhost:8080/v1/.well-known/ready
# Should return: {"status":"healthy"}
```

### 2. Install Python Dependencies

```powershell
pip install -r requirements.txt
```

### 3. Configure Environment

Update `.env` file with your settings:
```env
# OpenAI API Key (for extraction)
OPENAI_API_KEY=your_openai_api_key_here

# Weaviate Configuration
WEAVIATE_URL=http://localhost:8080
WEAVIATE_GRPC_PORT=50051

# Storage Configuration
LOCAL_STORAGE_PATH=cases/local_storage_md

# Chunking Configuration
CHUNK_SIZE_TOKENS=512
CHUNK_OVERLAP_TOKENS=51

# Template & Prompt Paths
MAIN_TEMPLATE_PATH=templates/main_template.json
PROMPTS_PATH=prompts/prompts.json

# Logging
LOG_LEVEL=INFO
```

## Quick Start

### Step 1: Initialize Weaviate Collections

```powershell
python src\scripts\init_weaviate.py
```

**Options:**
- `--force`: Recreate existing collections
- `--stats`: Show collection statistics
- `--delete`: Delete all collections (requires confirmation)

**Expected output:**
```
Creating collection: CaseDocuments
✓ Created: CaseDocuments
Creating collection: CaseMetadata
✓ Created: CaseMetadata
Creating collection: CaseSections
✓ Created: CaseSections
Creating collection: CaseChunks
✓ Created: CaseChunks

Collection Summary:
============================================================
CaseDocuments:
  Objects: 0
  No vectors

CaseMetadata:
  Objects: 0
  No vectors

CaseSections:
  Objects: 0
  Vector: all-mpnet-base-v2 (768-d)

CaseChunks:
  Objects: 0
  Vector: all-mpnet-base-v2 (768-d)
============================================================
```

### Step 2: Run Test Suite

```powershell
python test_weaviate_pipeline.py
```

**Individual tests:**
```powershell
# Single file ingestion
python test_weaviate_pipeline.py --test single

# Duplicate detection
python test_weaviate_pipeline.py --test duplicate

# Vector embeddings validation
python test_weaviate_pipeline.py --test embeddings

# Batch ingestion
python test_weaviate_pipeline.py --test batch
```

### Step 3: Ingest Your Documents

Create a simple ingestion script:

```python
from pathlib import Path
from src.pipelines.weaviate_ingestion_pipeline import WeaviateIngestionPipeline

# Initialize pipeline
pipeline = WeaviateIngestionPipeline()

# Ingest single file
result = pipeline.ingest_single(Path("cases/input_files/case1.pdf"))
print(f"Status: {result.status}")
print(f"File ID: {result.file_id}")
print(f"Sections: {result.sections_count}")
print(f"Chunks: {result.chunks_count}")

# Ingest batch
pdf_files = list(Path("cases/input_files").glob("*.pdf"))
results = pipeline.ingest_batch(pdf_files)

# Verify ingestion
counts = pipeline.verify_ingestion(result.file_id)
print(counts)

pipeline.close()
```

## Data Models

### 9 Extracted Sections

1. **summary**: Brief case overview
2. **introduction**: Background and context
3. **facts**: Facts of the case
4. **issues**: Legal issues raised
5. **arguments**: Arguments by parties
6. **judgment**: Court's judgment
7. **principles**: Legal principles established
8. **precedents**: Precedents cited
9. **outcome**: Final outcome

### Legal Metadata (13 fields)

- `case_number`: Unique case identifier
- `case_title`: Full case title
- `court_name`: Court name
- `judgment_date`: Date of judgment
- `sections_invoked`: IPC sections invoked
- `judges_coram`: Judges on bench
- `petitioner`: Petitioner name
- `respondent`: Respondent name
- `case_type`: Type of case (criminal, civil, etc.)
- `bench_strength`: Number of judges
- `citation`: Legal citation
- `counsel_petitioner`: Petitioner's counsel
- `counsel_respondent`: Respondent's counsel

## Pipeline Usage Examples

### Example 1: Basic Ingestion

```python
from src.pipelines.weaviate_ingestion_pipeline import WeaviateIngestionPipeline

pipeline = WeaviateIngestionPipeline()
result = pipeline.ingest_single("case.pdf")

if result.status == "success":
    print(f"✓ Ingested: {result.sections_count} sections, {result.chunks_count} chunks")
else:
    print(f"✗ Failed: {result.message}")

pipeline.close()
```

### Example 2: Batch Processing

```python
from pathlib import Path
from src.pipelines.weaviate_ingestion_pipeline import WeaviateIngestionPipeline

pipeline = WeaviateIngestionPipeline()

# Get all PDFs
pdf_files = list(Path("cases/input_files").glob("*.pdf"))

# Ingest batch
results = pipeline.ingest_batch(pdf_files, skip_existing=True)

# Print summary
for result in results:
    print(f"{result.file_id}: {result.status} - {result.message}")

pipeline.close()
```

### Example 3: Semantic Search

```python
from src.infrastructure.weaviate_client import WeaviateClient
from src.core.config import Config

client_wrapper = WeaviateClient(Config())
client = client_wrapper.client

# Search sections
sections = client.collections.get("CaseSections")
results = sections.query.near_text(
    query="what are the facts of the case",
    limit=5
)

for obj in results.objects:
    print(f"Section: {obj.properties['section_name']}")
    print(f"Text: {obj.properties['text'][:200]}...")
    print()

client_wrapper.close()
```

### Example 4: Hybrid Search (BM25 + Vector)

```python
from src.infrastructure.weaviate_client import WeaviateClient
from src.core.config import Config

client_wrapper = WeaviateClient(Config())
client = client_wrapper.client

# Hybrid search on chunks
chunks = client.collections.get("CaseChunks")
results = chunks.query.hybrid(
    query="section 302 IPC murder conviction",
    alpha=0.5,  # 0.5 = balanced BM25 and vector search
    limit=10
)

for obj in results.objects:
    print(f"Chunk {obj.properties['chunk_index']}: {obj.properties['text'][:150]}...")

client_wrapper.close()
```

## Troubleshooting

### Issue: Weaviate connection error

**Solution:**
```powershell
# Check if Weaviate is running
docker ps | Select-String weaviate

# Start Weaviate if stopped
docker start weaviate

# Check health
curl http://localhost:8080/v1/.well-known/ready
```

### Issue: OpenAI API errors

**Solution:**
- Verify API key in `.env`
- Check API quota/limits
- Ensure GPT-4o access enabled

### Issue: Out of memory during batch ingestion

**Solution:**
- Reduce batch size in `ingest_batch()`
- Process files in smaller batches
- Increase Docker memory allocation

### Issue: Embeddings not normalized

**Solution:**
- Check `EmbeddingService.embed_batch(normalize=True)`
- Verify vector magnitude ≈ 1.0 using test script

## Performance Tips

1. **Batch Processing**: Use `ingest_batch()` for multiple files
2. **Parallel Embedding**: EmbeddingService uses batch_size=32
3. **Weaviate Batching**: Uses dynamic batching for efficient inserts
4. **Deduplication**: Content-addressed storage prevents re-processing

## Monitoring

### Collection Statistics

```powershell
python src\scripts\init_weaviate.py --stats
```

### Verify Specific File

```python
from src.pipelines.weaviate_ingestion_pipeline import WeaviateIngestionPipeline

pipeline = WeaviateIngestionPipeline()
counts = pipeline.verify_ingestion(file_id="your-file-id-here")
print(counts)
# Expected: {'documents': 1, 'metadata': 1, 'sections': 9, 'chunks': N}
```

## Architecture Decisions

### Why 4 Collections?

- **Separation of concerns**: Metadata, sections, chunks serve different query patterns
- **Flexible retrieval**: Query sections for high-level understanding, chunks for specific details
- **Efficient storage**: Only sections/chunks have vectors (768-d each)

### Why L2 Normalization?

- Enables cosine similarity search in Weaviate
- Magnitude = 1.0 for all vectors
- Faster distance calculations

### Why Content-Addressed Storage?

- **Deduplication**: Same content = same hash = skip reprocessing
- **Integrity**: Hash verifies content hasn't changed
- **Deterministic**: Reproducible file IDs across runs

## Migration from PostgreSQL

This pipeline **completely replaces** the old PostgreSQL+pgvector architecture. Key differences:

| Feature | Old (PostgreSQL) | New (Weaviate) |
|---------|------------------|----------------|
| Collections | 1 table | 4 collections |
| Embeddings | Facts + Metadata | Sections + Chunks |
| Storage | Database BLOBs | Local filesystem |
| Search | pgvector | Native hybrid search |
| Deduplication | None | SHA-256 hash |

**No backward compatibility**: Old data must be re-ingested using new pipeline.

## Support

For issues or questions:
1. Check logs in `logs/` directory
2. Run test suite: `python test_weaviate_pipeline.py`
3. Verify Weaviate health: `curl http://localhost:8080/v1/.well-known/ready`
4. Check `.env` configuration

## Next Steps

1. ✅ Initialize Weaviate collections
2. ✅ Run test suite
3. 🔄 Ingest your case documents
4. 🔄 Build search/retrieval UI
5. 🔄 Implement RAG pipeline for case analysis

---

**Documentation Version**: 1.0  
**Last Updated**: 2024-01-10  
**Pipeline Version**: Weaviate 4.9+ / Haystack 2.0+
