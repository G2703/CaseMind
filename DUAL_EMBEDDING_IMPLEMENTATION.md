# Dual Embedding System Implementation

## Overview
Implemented a dual-embedding system that stores TWO separate embeddings per legal case document:
1. **Facts Embedding** (stored in `embedding` column) - Generated from the complete filled template with ALL extracted facts
2. **Metadata Embedding** (stored in `embedding_metadata` column) - Generated from concatenated metadata fields

## Architecture Changes

### 1. Database Schema (`src/scripts/init_database.py`)
- Added `add_metadata_embedding_column()` function to create the second embedding column
- Modified `create_schema()` to support dual embeddings
- Updated `verify_setup()` to check both embedding columns exist
- Added HNSW index on `embedding_metadata` column for efficient metadata-based search

**Schema Structure:**
```sql
haystack_documents:
  - id (text, primary key)
  - content (text) - stores facts_summary for display
  - meta (jsonb) - stores all metadata and extracted_facts
  - embedding (vector(768)) - facts embedding (from full template)
  - embedding_metadata (vector(768)) - metadata embedding
```

### 2. Custom Components (`src/pipelines/haystack_custom_nodes.py`)

#### New: `DualEmbedderNode`
Replaces the standard `SentenceTransformersDocumentEmbedder` and `DocumentWriter`.
- **Facts Embedding**: Formats entire extracted facts template (all tiers, all fields) as text and embeds it
- **Metadata Embedding**: Concatenates metadata fields (case_title, court_name, judgment_date, sections_invoked, most_appropriate_section)
- **Custom SQL**: Uses psycopg2 to insert both embeddings into PostgreSQL
- **Sets doc.content**: Updates to facts_summary for retrieval display

#### New: `FactsEmbeddingRetriever`
Custom retriever that searches on the `embedding` column (facts embedding).
- Replaces `PgvectorEmbeddingRetriever`
- Uses direct SQL for fine-grained control
- Searches based on facts similarity (default behavior)
- Returns documents with cosine similarity scores

#### Modified: `FactExtractorNode`
- **Removed** `doc.content = facts_summary` line
- Keeps original content intact for DualEmbedderNode processing
- Still generates facts_summary and stores in metadata

### 3. Ingestion Pipeline (`src/pipelines/haystack_ingestion_pipeline.py`)

**Pipeline Flow:**
```
PDF → Markdown → MetadataExtractor → DuplicateChecker → 
TemplateLoader → FactExtractor → DualEmbedder → [DB Storage]
```

**Changes:**
- Removed `SentenceTransformersDocumentEmbedder`
- Removed `DocumentWriter`
- Added `DualEmbedderNode` which handles both embedding creation AND database storage
- Updated result extraction to check `dual_embedder` output instead of `writer`
- Updated imports

### 4. Similarity Search Pipeline (`src/pipelines/pure_haystack_similarity_pipeline.py`)

**Changes:**
- Replaced `PgvectorEmbeddingRetriever` with `FactsEmbeddingRetriever`
- Now searches on facts embedding by default (no parameter needed)
- Updated imports and logging messages

## What Gets Embedded

### Facts Embedding (PRIMARY SEARCH)
**Source**: Complete filled template from fact extraction
**Format**: Recursive text extraction including ALL fields and values
**Example**:
```
tier_1_parties.appellant: John Doe | tier_1_parties.respondent: State of Maharashtra | 
tier_2_incident.date: 2024-01-15 | tier_2_incident.location: Mumbai | 
tier_3_legal.sections[0]: IPC 302 | tier_3_legal.arguments: Self-defense claimed | ...
```

### Metadata Embedding (FOR FUTURE METADATA-ONLY SEARCH)
**Source**: Key metadata fields
**Format**: Simple concatenation
**Example**:
```
State of Maharashtra vs. John Doe High Court of Bombay 2024-03-20 IPC 302 IPC 307 IPC 302
```

## Search Behavior

**Current Implementation:**
- Searches ONLY on facts embedding (via FactsEmbeddingRetriever)
- Metadata embedding is stored but not currently used for search
- Ready for future enhancement to add metadata-only search option

**Future Enhancement Option:**
Create a `MetadataEmbeddingRetriever` similar to `FactsEmbeddingRetriever` that searches on `embedding_metadata` column for metadata-only searches.

## Database Re-initialization Required

**IMPORTANT**: Existing data is NOT compatible. You must:

1. **Re-initialize database:**
   ```powershell
   python src/scripts/init_database.py
   ```
   This will add the `embedding_metadata` column to existing tables.

2. **Re-ingest all cases:**
   All existing cases need to be re-ingested to generate both embeddings.
   Previous single-embedding data will not work with the new retrieval system.

## Benefits

1. **Richer Facts Search**: Embedding captures the ENTIRE template structure, not just a summary
2. **Future Metadata Search**: Can add metadata-only search later without re-ingestion
3. **Flexible Retrieval**: Can potentially combine both embeddings for hybrid search
4. **Better Semantic Coverage**: Full template provides more context for similarity matching

## Testing

After implementation, test by:

1. Re-initialize database
2. Ingest a few test cases
3. Run similarity search
4. Verify both embeddings are being created and stored
5. Check that search results are based on facts similarity

## Files Modified

1. `src/scripts/init_database.py` - Schema changes
2. `src/pipelines/haystack_custom_nodes.py` - New components
3. `src/pipelines/haystack_ingestion_pipeline.py` - Pipeline updates
4. `src/pipelines/pure_haystack_similarity_pipeline.py` - Retrieval updates
