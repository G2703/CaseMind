# Weaviate Migration - Step-by-Step Checklist

This checklist guides you through migrating from the old PostgreSQL+pgvector architecture to the new Weaviate-based system.

---

## ⚠️ Important Notes

- **No Backward Compatibility**: Old PostgreSQL data will NOT be automatically migrated
- **Complete Overwrite**: This is a fresh start with a new architecture
- **Re-ingestion Required**: All case documents must be re-ingested using the new pipeline
- **Data Loss**: Old data in PostgreSQL will remain but won't be used by the new system

---

## Pre-Migration Checklist

### ☐ 1. Backup Existing Data (Optional)

If you want to keep your old PostgreSQL data:

```powershell
# Export PostgreSQL data
pg_dump -U your_user -d casemind > backup_casemind.sql

# Or backup using pgAdmin GUI
```

### ☐ 2. Verify Prerequisites

- [ ] **Python 3.9+** installed
  ```powershell
  python --version
  # Should show Python 3.9 or higher
  ```

- [ ] **Docker** installed and running
  ```powershell
  docker --version
  docker ps
  ```

- [ ] **Git** (if cloning/pulling updates)
  ```powershell
  git --version
  ```

- [ ] **OpenAI API Key** (for LLM extraction)
  - Get key from: https://platform.openai.com/api-keys
  - Ensure GPT-4o access is enabled

### ☐ 3. Review System Requirements

- **Disk Space**: 
  - Weaviate database: ~10GB minimum
  - Local markdown storage: ~100MB per 1000 documents
  - Python dependencies: ~500MB

- **RAM**: 
  - Minimum: 8GB
  - Recommended: 16GB+ (for large batch processing)

- **CPU**: 
  - Multi-core recommended for faster embedding generation

---

## Installation Steps

### ☐ Step 1: Install Weaviate with Docker

```powershell
# Pull Weaviate image
docker pull semitechnologies/weaviate:latest

# Run Weaviate container
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

# Verify Weaviate is running
curl http://localhost:8080/v1/.well-known/ready
# Expected: {"status":"healthy"}
```

**Troubleshooting:**
- If port 8080 is in use: Change `-p 8080:8080` to `-p 8081:8080` and update `.env`
- If container fails to start: Check Docker logs with `docker logs weaviate`

### ☐ Step 2: Install Python Dependencies

```powershell
# Navigate to CaseMind directory
cd C:\Users\gayat\OneDrive\Documents\GitHub\CaseMind

# Install/upgrade pip
python -m pip install --upgrade pip

# Install dependencies
pip install -r requirements.txt

# Verify key packages
pip show weaviate-client weaviate-haystack sentence-transformers openai
```

**Expected packages:**
- weaviate-client >= 4.9.0
- weaviate-haystack >= 1.0.0
- sentence-transformers >= 2.2.0
- openai >= 1.0.0
- haystack-ai >= 2.0.0

### ☐ Step 3: Configure Environment Variables

Update your `.env` file:

```env
# OpenAI Configuration
OPENAI_API_KEY=sk-your-actual-api-key-here

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

# Embedding Model
EMBEDDING_MODEL=sentence-transformers/all-mpnet-base-v2

# Logging
LOG_LEVEL=INFO
```

**Verify configuration:**
```powershell
# Test OpenAI API key
python -c "from openai import OpenAI; import os; client = OpenAI(api_key=os.getenv('OPENAI_API_KEY')); print('✓ OpenAI API key valid')"

# Test Weaviate connection
python -c "from src.infrastructure.weaviate_client import WeaviateClient; from src.core.config import Config; client = WeaviateClient(Config()); print('✓ Weaviate connected' if client.is_ready() else '✗ Weaviate not ready'); client.close()"
```

### ☐ Step 4: Create Required Directories

```powershell
# Create local storage directory
New-Item -ItemType Directory -Force -Path "cases\local_storage_md"

# Create logs directory
New-Item -ItemType Directory -Force -Path "logs"

# Verify structure
Get-ChildItem -Directory
```

---

## Weaviate Setup

### ☐ Step 5: Initialize Weaviate Collections

```powershell
# Initialize all 4 collections
python src\scripts\init_weaviate.py

# Expected output:
# Creating collection: CaseDocuments
# ✓ Created: CaseDocuments
# Creating collection: CaseMetadata
# ✓ Created: CaseMetadata
# Creating collection: CaseSections
# ✓ Created: CaseSections
# Creating collection: CaseChunks
# ✓ Created: CaseChunks
```

**Troubleshooting:**
- If collections already exist: Use `--force` flag to recreate
  ```powershell
  python src\scripts\init_weaviate.py --force
  ```
- If schema errors occur: Check Weaviate version compatibility

### ☐ Step 6: Verify Collections

```powershell
# Show collection statistics
python src\scripts\init_weaviate.py --stats

# Expected output:
# CaseDocuments: 0 objects
# CaseMetadata: 0 objects
# CaseSections: 0 objects
# CaseChunks: 0 objects
```

---

## Testing

### ☐ Step 7: Run Test Suite

```powershell
# Run all tests
python test_weaviate_pipeline.py

# Or run individual tests
python test_weaviate_pipeline.py --test single      # Single file ingestion
python test_weaviate_pipeline.py --test duplicate   # Duplicate detection
python test_weaviate_pipeline.py --test embeddings  # Vector embeddings
python test_weaviate_pipeline.py --test batch       # Batch ingestion
```

**Expected results:**
- ✓ PASS: Single File Ingestion
- ✓ PASS: Duplicate Detection
- ✓ PASS: Vector Embeddings
- ✓ PASS: Batch Ingestion

**If tests fail:**
1. Check test output for specific errors
2. Verify Weaviate is running
3. Check OpenAI API key and quota
4. Ensure PDF files exist in `cases/input_files/`

---

## Data Migration

### ☐ Step 8: Prepare Source Documents

```powershell
# Ensure your PDF files are in the input directory
Get-ChildItem -Path "cases\input_files" -Filter "*.pdf"

# If PDFs are elsewhere, copy them:
Copy-Item -Path "path\to\your\pdfs\*" -Destination "cases\input_files\" -Include "*.pdf"
```

### ☐ Step 9: Test Single File Ingestion

```powershell
# Ingest one file first to verify everything works
python ingest_cli.py ingest --file "cases\input_files\your-test-file.pdf"

# Expected output:
# Ingesting file: your-test-file.pdf
# ✓ Success!
#   File ID: abc123...
#   Sections: 9
#   Chunks: 42
#   Case: Your Case Title
```

**Verify ingestion:**
```powershell
# Use the file_id from above output
python ingest_cli.py verify --file-id "abc123..."

# Expected:
# Verification results:
#   Documents: 1
#   Metadata: 1
#   Sections: 9
#   Chunks: 42
```

### ☐ Step 10: Batch Ingest All Documents

```powershell
# Ingest all PDFs in directory
python ingest_cli.py ingest --directory "cases\input_files"

# Or use helper script with menu
.\run_weaviate.ps1 ingest -Path "cases\input_files"

# For large batches, monitor progress in logs/
```

**Performance tips:**
- **Small batches (< 100 files)**: Run directly
- **Large batches (100-1000 files)**: Process in chunks
  ```powershell
  # Process first 100 files
  Get-ChildItem "cases\input_files\*.pdf" | Select-Object -First 100 | ForEach-Object {
      python ingest_cli.py ingest --file $_.FullName
  }
  ```
- **Very large batches (1000+ files)**: Run overnight or on dedicated machine

### ☐ Step 11: Verify Batch Ingestion

```powershell
# Check collection statistics
python src\scripts\init_weaviate.py --stats

# Expected ratios:
# If you ingested N files:
#   CaseDocuments: N
#   CaseMetadata: N
#   CaseSections: ~9*N (some cases may have fewer)
#   CaseChunks: variable (depends on document length)
```

---

## Validation

### ☐ Step 12: Test Search Functionality

```powershell
# Test semantic search
python ingest_cli.py search --query "what are the facts of the case" --limit 5

# Test different queries
python ingest_cli.py search --query "section 302 IPC" --limit 10
python ingest_cli.py search --query "precedents cited" --limit 5
```

### ☐ Step 13: Verify Data Quality

Create a quick validation script:

```python
# validate_migration.py
from src.infrastructure.weaviate_client import WeaviateClient
from src.core.config import Config

client_wrapper = WeaviateClient(Config())
client = client_wrapper.client

# Sample sections
sections = client.collections.get("CaseSections")
results = sections.query.fetch_objects(limit=10, include_vector=True)

print(f"Sampled {len(results.objects)} sections:")
for obj in results.objects:
    section_name = obj.properties.get("section_name")
    text_length = len(obj.properties.get("text", ""))
    has_vector = obj.vector is not None
    
    print(f"  ✓ Section: {section_name}, Text: {text_length} chars, Vector: {has_vector}")

client_wrapper.close()
```

Run validation:
```powershell
python validate_migration.py
```

---

## Post-Migration

### ☐ Step 14: Update Application Code

If you have existing code that used PostgreSQL:

**Old code (PostgreSQL):**
```python
from haystack.document_stores import PgvectorDocumentStore
document_store = PgvectorDocumentStore(...)
```

**New code (Weaviate):**
```python
from src.pipelines.weaviate_ingestion_pipeline import WeaviateIngestionPipeline
pipeline = WeaviateIngestionPipeline()
```

### ☐ Step 15: Decommission PostgreSQL (Optional)

**Only after confirming Weaviate is working!**

```powershell
# Stop PostgreSQL service
Stop-Service postgresql-x64-14  # Adjust version as needed

# Or uninstall via Control Panel if no longer needed
```

### ☐ Step 16: Setup Backup Strategy

```powershell
# Create backup script for Weaviate
# Save as backup_weaviate.ps1

$backupDir = "backups\weaviate_$(Get-Date -Format 'yyyyMMdd_HHmmss')"
New-Item -ItemType Directory -Force -Path $backupDir

# Backup Weaviate data
docker exec weaviate tar czf - /var/lib/weaviate | Set-Content "$backupDir\weaviate_data.tar.gz" -Encoding Byte

# Backup local markdown storage
Compress-Archive -Path "cases\local_storage_md\*" -DestinationPath "$backupDir\markdown_storage.zip"

Write-Host "✓ Backup created: $backupDir"
```

---

## Troubleshooting Guide

### Issue: "Weaviate connection failed"

**Solution:**
```powershell
# Check if Weaviate is running
docker ps | Select-String weaviate

# If not running, start it
docker start weaviate

# Check logs
docker logs weaviate
```

### Issue: "OpenAI API rate limit exceeded"

**Solution:**
- Wait 60 seconds between requests
- Upgrade OpenAI plan for higher limits
- Reduce batch size

### Issue: "Out of memory during ingestion"

**Solution:**
```powershell
# Process in smaller batches
Get-ChildItem "cases\input_files\*.pdf" | Select-Object -First 10 | ForEach-Object {
    python ingest_cli.py ingest --file $_.FullName
    Start-Sleep -Seconds 5
}

# Increase Docker memory
# Docker Desktop > Settings > Resources > Memory > 8GB+
```

### Issue: "Embeddings are not normalized"

**Solution:**
- Check `EmbeddingService.embed_batch(normalize=True)`
- Re-run ingestion for affected files
- Verify with: `python test_weaviate_pipeline.py --test embeddings`

### Issue: "Duplicate detection not working"

**Solution:**
- Verify markdown normalization is consistent
- Check if hash computation is deterministic
- Re-initialize collections if schema changed

---

## Performance Benchmarks

Expected processing times (on mid-range hardware):

| Task | Time |
|------|------|
| Single PDF (10 pages) | ~30 seconds |
| Batch (100 PDFs) | ~45 minutes |
| Batch (1000 PDFs) | ~8 hours |
| Semantic search query | ~100ms |
| Hybrid search query | ~150ms |

---

## Rollback Plan

If you need to revert to PostgreSQL:

### ☐ Rollback Step 1: Restore PostgreSQL

```powershell
# Restore database from backup
psql -U your_user -d casemind < backup_casemind.sql
```

### ☐ Rollback Step 2: Reinstall Old Dependencies

```powershell
pip install pgvector-haystack psycopg2-binary
```

### ☐ Rollback Step 3: Revert Configuration

Restore old `config.py` from version control:
```powershell
git checkout HEAD~1 -- src/core/config.py
```

---

## Success Criteria

Migration is successful when:

- ✅ All 4 Weaviate collections are created
- ✅ All test cases pass
- ✅ Documents are successfully ingested
- ✅ Semantic search returns relevant results
- ✅ Duplicate detection works
- ✅ Vector embeddings are L2 normalized
- ✅ Collection counts follow 1:1:9:N ratio

---

## Next Steps After Migration

1. **Build RAG Pipeline**: Use sections/chunks for question-answering
2. **Create Search UI**: Frontend for semantic/hybrid search
3. **Implement Analytics**: Case analysis using extracted metadata
4. **Setup Monitoring**: Track ingestion metrics and search performance
5. **Optimize**: Tune chunk size, overlap, and search parameters

---

## Support Resources

- **Quick Start Guide**: `WEAVIATE_QUICKSTART.md`
- **Implementation Summary**: `IMPLEMENTATION_SUMMARY.md`
- **Test Suite**: `test_weaviate_pipeline.py`
- **Weaviate Docs**: https://weaviate.io/developers/weaviate
- **Haystack Docs**: https://docs.haystack.deepset.ai/

---

**Migration Checklist Version**: 1.0  
**Last Updated**: 2024-01-10  
**Estimated Time**: 2-4 hours (excluding large batch ingestion)
