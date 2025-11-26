# Quick Start Guide: Optimized CaseMind Pipeline

## Overview
The CaseMind ingestion pipeline has been optimized for:
- **Token efficiency** (70% reduction in fact extraction)
- **Comprehensive extraction** (7-section case summary + template-based facts)
- **Multi-field embeddings** (8 embeddings per case for flexible search)

---

## What Changed?

### Before:
```
PDF → Markdown → Extract Metadata → Template → Extract Facts → Store
```

### After:
```
PDF → Markdown → Comprehensive Summarization (7 sections) → 
  → Create 7 Embeddings → Template Selection → 
  → Extract Facts (using summary, not full text) → 
  → Create Facts Embedding → Store in legal_cases table
```

---

## Quick Start

### 1. Verify Installation

Run the test script to verify everything is set up:

```powershell
python test_optimized_pipeline.py
```

This will:
- ✓ Check database connection
- ✓ Verify `legal_cases` table exists
- ✓ Show table schema
- ✓ Allow you to test ingestion with a sample PDF

### 2. Ingest Your First Case

```python
import asyncio
from pathlib import Path
from src.pipelines.haystack_ingestion_pipeline import HaystackIngestionPipeline

async def ingest_case():
    pipeline = HaystackIngestionPipeline()
    result = await pipeline.ingest_single(Path("path/to/your/case.pdf"))
    
    print(f"Status: {result.status}")
    print(f"Case ID: {result.case_id}")
    print(f"Case Title: {result.metadata.case_title}")

asyncio.run(ingest_case())
```

### 3. Check the Database

```sql
-- See all ingested cases
SELECT case_id, case_title, case_id FROM legal_cases;

-- View full summary for a case
SELECT summary FROM legal_cases WHERE case_id = 'your_case_id';

-- View filled template
SELECT factual_summary FROM legal_cases WHERE case_id = 'your_case_id';
```

---

## Database Schema

The new `legal_cases` table contains:

| Column | Type | Purpose |
|--------|------|---------|
| `file_id` | VARCHAR | Primary key (document ID) |
| `case_id` | VARCHAR | Case number from judgment |
| `case_title` | VARCHAR | Case title |
| `file_hash` | VARCHAR | For duplicate detection |
| `summary` | JSONB | Complete 7-section summary |
| `metadata_embedding` | vector(768) | Embedding of metadata section |
| `case_facts_embedding` | vector(768) | Embedding of case facts |
| `issues_embedding` | vector(768) | Embedding of legal issues |
| `evidence_embedding` | vector(768) | Embedding of evidence |
| `arguments_embedding` | vector(768) | Embedding of arguments |
| `reasoning_embedding` | vector(768) | Embedding of court reasoning |
| `judgement_embedding` | vector(768) | Embedding of judgement |
| `factual_summary` | JSONB | Template filled with extracted facts |
| `facts_embedding` | vector(768) | **PRIMARY search embedding** |

---

## What Gets Extracted?

### Summary (Phase 1):
1. **Metadata**: case number, title, court, dates, parties, sections, lower court history
2. **Case Facts**: prosecution version, defence version, timeline, location, motive
3. **Issues**: Legal questions for determination
4. **Evidence**: witnesses, medical, forensic, documentary, recovery, expert opinions, investigation
5. **Arguments**: Prosecution and defence arguments
6. **Reasoning**: Court's analysis, credibility assessment, legal principles
7. **Judgement**: Final decision, sentence/bail conditions, directions

### Factual Summary (Phase 2):
- Template-specific facts extracted from case_facts + evidence
- Structured according to the legal section (e.g., IPC 376, IPC 302)
- Used to create the **primary search embedding**

---

## Token Optimization

### Old Approach:
```
Fact Extraction: Send ENTIRE markdown (10,000+ tokens) → Extract facts
```

### New Approach:
```
1. Summarization: Send full markdown → Get structured 7-section summary
2. Fact Extraction: Send ONLY case_facts + evidence JSON (~2,000 tokens) → Extract facts
```

**Result**: ~70% token reduction in Phase 2, better quality extraction

---

## Search Strategy

### Current:
- User query → Embed → Compare with `facts_embedding` → Retrieve similar cases

### Future Enhancements:
- Multi-field search: Search across specific sections (evidence, reasoning, etc.)
- Hybrid search: Combine multiple embedding similarities
- Weighted search: Different weights for different sections

---

## Troubleshooting

### Issue: "legal_cases table not found"
**Solution**: The table is auto-created on first pipeline run. Just run the pipeline once.

### Issue: "Duplicate document" error
**Solution**: The file has already been ingested. Check `legal_cases` table with the file hash.

### Issue: "Fact extraction failed"
**Solution**: 
- Check that templates exist in `templates/` directory
- Verify template for the specific section (e.g., `ipc_376.json`)
- Check logs for detailed error messages

### Issue: "Database connection failed"
**Solution**:
- Verify PostgreSQL is running
- Check `config.json` for correct database credentials
- Ensure pgvector extension is installed

---

## File Structure

```
CaseMind/
├── src/
│   └── pipelines/
│       ├── haystack_ingestion_pipeline.py  # Updated main pipeline
│       ├── haystack_custom_nodes.py        # Old nodes (preserved)
│       └── haystack_custom_nodes_v2.py     # New optimized nodes
├── templates/
│   ├── ipc_302.json                        # Murder
│   ├── ipc_376.json                        # Rape
│   ├── legal_case.json                     # Generic fallback
│   └── ...
├── test_optimized_pipeline.py              # Test script
├── PIPELINE_OPTIMIZATION_SUMMARY.md        # Detailed documentation
└── QUICK_START.md                          # This file
```

---

## Next Steps

1. **Test**: Run `test_optimized_pipeline.py`
2. **Ingest**: Process your case PDFs
3. **Verify**: Check `legal_cases` table
4. **Search**: Implement similarity search using `facts_embedding`
5. **Analyze**: Use other 7 embeddings for advanced analytics

---

## Support

For issues or questions:
1. Check logs in `logs/` directory
2. Review `PIPELINE_OPTIMIZATION_SUMMARY.md` for detailed architecture
3. Inspect database with SQL queries
4. Check Haystack documentation for component details

---

## Key Takeaways

✅ **Automatic table creation** - No manual DB setup needed  
✅ **Token efficient** - 70% reduction in fact extraction  
✅ **Comprehensive data** - 7-section summary + template facts  
✅ **Multi-field embeddings** - 8 embeddings for flexible search  
✅ **Backward compatible** - Old data preserved  
✅ **Error resilient** - Rollback on failure  

**You're ready to go! Start with `test_optimized_pipeline.py` to verify everything works.**
