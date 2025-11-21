# Haystack 2.0 Integration Guide

## Overview

CaseMind has been refactored to use **Haystack 2.0** - a modern, production-ready AI orchestration framework. This guide explains the new architecture, components, and how to use them.

## Architecture

### Core Principles

The new architecture follows Haystack's component-based design:

1. **Components**: Modular, reusable building blocks (embedders, retrievers, rankers)
2. **Pipelines**: Declarative composition of components with automatic optimization
3. **Document Store**: Centralized vector database (PostgreSQL + pgvector via Haystack)
4. **Documents**: Standardized data structure for text and metadata

### Component Mapping

| Function | Old Implementation | New Haystack Component |
|----------|-------------------|------------------------|
| Document Storage | Custom `PGVectorDocumentStore` | `haystack_integrations.document_stores.pgvector.PgvectorDocumentStore` |
| Text Embedding | Custom `EmbeddingService` | `haystack.components.embedders.SentenceTransformersTextEmbedder` |
| Document Embedding | Custom batch embedding | `haystack.components.embedders.SentenceTransformersDocumentEmbedder` |
| Vector Retrieval | Custom SQL queries | `haystack_integrations.components.retrievers.pgvector.PgvectorEmbeddingRetriever` |
| Re-ranking | Custom cross-encoder | `haystack.components.rankers.TransformersSimilarityRanker` |
| Pipeline Orchestration | Manual Python code | `haystack.Pipeline` with component connections |

## New Components

### 1. HaystackDocumentStoreWrapper

**Location**: `src/infrastructure/haystack_document_store.py`

Wraps Haystack's `PgvectorDocumentStore` with CaseMind-specific features:

- **Dual embeddings**: Stores both facts and metadata embeddings
- **Backward compatibility**: Same interface as old `PGVectorDocumentStore`
- **Enhanced querying**: Supports both embedding types for retrieval

```python
from infrastructure.haystack_document_store import HaystackDocumentStoreWrapper

# Initialize (singleton pattern)
store = HaystackDocumentStoreWrapper()

# Write document with dual embeddings
store.write_document(
    doc_id=case_id,
    content=full_text,
    metadata=case_metadata,
    embedding_facts=facts_vector,
    embedding_metadata=metadata_vector,
    file_hash=file_hash,
    original_filename=filename
)

# Query by embedding
results = store.query_by_embedding(
    embedding=query_vector,
    top_k=10,
    embedding_field="embedding_facts",  # or "embedding_metadata"
    exclude_id=query_case_id
)

# Access underlying Haystack store for pipelines
haystack_store = store.get_haystack_store()
```

### 2. HaystackEmbeddingService

**Location**: `src/services/haystack_embedding_service.py`

Uses Haystack's SentenceTransformers components:

```python
from services.haystack_embedding_service import HaystackEmbeddingService

embedder = HaystackEmbeddingService()

# Embed single text (for queries)
query_embedding = embedder.embed_text("Legal case query text")

# Embed multiple texts
embeddings = embedder.embed_texts(["text1", "text2", "text3"])

# Embed Haystack Documents
from haystack import Document
docs = [Document(content="Case facts...")]
embedded_docs = embedder.embed_documents(docs)
```

### 3. HaystackRankerService

**Location**: `src/services/haystack_ranker_service.py`

Cross-encoder re-ranking using Haystack's `TransformersSimilarityRanker`:

```python
from services.haystack_ranker_service import HaystackRankerService

ranker = HaystackRankerService()

# Rank documents
ranked_docs = ranker.rank_documents(
    query="Query text",
    documents=candidate_documents,
    top_k=5
)

# Each document now has a .score attribute
for doc in ranked_docs:
    print(f"{doc.meta['case_title']}: {doc.score}")
```

### 4. ThresholdFilterComponent

Custom Haystack component for score-based filtering:

```python
from services.haystack_ranker_service import ThresholdFilterComponent

filter_component = ThresholdFilterComponent(threshold=0.5)

# Use in pipeline or standalone
result = filter_component.run(documents=scored_documents)
filtered_docs = result["documents"]
```

### 5. HaystackSimilarityPipeline

**Location**: `src/pipelines/haystack_similarity_pipeline.py`

Complete similarity search pipeline using native Haystack Pipeline:

```python
from pipelines.haystack_similarity_pipeline import HaystackSimilarityPipeline
from pathlib import Path

pipeline = HaystackSimilarityPipeline()

# Run similarity search
result = await pipeline.run_full_pipeline(
    file_path=Path("case.pdf"),
    use_metadata_query=False  # True for metadata-based search
)

# Visualize pipeline structure
print(pipeline.get_pipeline_graph())
```

## Pipeline Architecture

The new similarity pipeline is a Haystack Pipeline with these components:

```
Query PDF
    ↓
[Ingestion Pipeline]
    ↓
Query Text/Embedding
    ↓
┌─────────────────────────────────────┐
│   Haystack Retrieval Pipeline       │
│                                     │
│  1. PgvectorEmbeddingRetriever      │
│     - Searches vector database      │
│     - Returns top candidates (3x)   │
│                                     │
│  2. TransformersSimilarityRanker    │
│     - Re-ranks with cross-encoder   │
│     - Adds precision scores         │
│                                     │
│  3. ThresholdFilterComponent        │
│     - Filters low-scoring results   │
│     - Returns only relevant cases   │
│                                     │
└─────────────────────────────────────┘
    ↓
Similar Cases Result
```

## Dual Embedding Strategy

CaseMind uses **two embeddings per document**:

1. **Facts Embedding** (`embedding_facts`): Based on case facts and circumstances
2. **Metadata Embedding** (`embedding_metadata`): Based on legal sections, court, dates

### How It Works

**Storage**:
```python
# Primary embedding (facts) stored in Document.embedding
# Secondary embedding (metadata) stored in Document.meta['_embedding_metadata']
doc = Document(
    id=case_id,
    content=facts_text,
    embedding=facts_vector,
    meta={
        '_embedding_metadata': metadata_vector,
        'case_title': '...',
        # other metadata
    }
)
```

**Retrieval**:
```python
# Search by facts (default)
results = store.query_by_embedding(
    embedding=query_vector,
    embedding_field="embedding_facts"
)

# Search by metadata (sections, court, etc.)
results = store.query_by_embedding(
    embedding=query_vector,
    embedding_field="embedding_metadata"
)
```

## Migration from Old Implementation

### Step 1: Update Dependencies

```bash
pip install -r requirements.txt
```

New packages:
- `haystack-ai>=2.0.0`
- `pgvector-haystack`
- `sentence-transformers-haystack`

### Step 2: Update Imports

**Old**:
```python
from infrastructure.document_store import PGVectorDocumentStore
from services.embedding_service import EmbeddingService
from pipelines.similarity_pipeline import SimilaritySearchPipeline
```

**New**:
```python
from infrastructure.haystack_document_store import HaystackDocumentStoreWrapper as PGVectorDocumentStore
from services.haystack_embedding_service import HaystackEmbeddingService as EmbeddingService
from pipelines.haystack_similarity_pipeline import HaystackSimilarityPipeline as SimilaritySearchPipeline
```

**OR use backward compatibility aliases** (no import changes needed):
```python
# These still work!
from infrastructure.document_store import PGVectorDocumentStore  # → HaystackDocumentStoreWrapper
from services.embedding_service import EmbeddingService  # → HaystackEmbeddingService
from pipelines.similarity_pipeline import SimilaritySearchPipeline  # → HaystackSimilarityPipeline
```

### Step 3: Test Migration

Run the migration test script:
```bash
python src/scripts/test_haystack_migration.py
```

### Step 4: View Migration Report

```bash
python src/scripts/haystack_migration_report.py
```

## Advanced Usage

### Building Custom Pipelines

```python
from haystack import Pipeline
from haystack_integrations.components.retrievers.pgvector import PgvectorEmbeddingRetriever
from haystack.components.rankers import TransformersSimilarityRanker

# Create custom pipeline
pipeline = Pipeline()

# Add components
pipeline.add_component("retriever", PgvectorEmbeddingRetriever(
    document_store=store.get_haystack_store(),
    top_k=20
))
pipeline.add_component("ranker", TransformersSimilarityRanker(
    model="cross-encoder/ms-marco-MiniLM-L6-v2"
))

# Connect components
pipeline.connect("retriever.documents", "ranker.documents")

# Run pipeline
result = pipeline.run({
    "retriever": {"query_embedding": query_vector},
    "ranker": {"query": query_text, "top_k": 5}
})

similar_docs = result["ranker"]["documents"]
```

### Adding Custom Components

Create a Haystack component:

```python
from haystack import component, Document
from typing import List

@component
class CustomFilterComponent:
    """Custom component for domain-specific filtering."""
    
    def __init__(self, min_year: int):
        self.min_year = min_year
    
    @component.output_types(documents=List[Document])
    def run(self, documents: List[Document]) -> dict:
        """Filter documents by judgment year."""
        filtered = []
        for doc in documents:
            year_str = doc.meta.get('judgment_date', '').split('-')[0]
            if year_str.isdigit() and int(year_str) >= self.min_year:
                filtered.append(doc)
        
        return {"documents": filtered}

# Use in pipeline
pipeline.add_component("year_filter", CustomFilterComponent(min_year=2020))
pipeline.connect("ranker.documents", "year_filter.documents")
```

### Metadata Filtering

```python
from haystack.document_stores.types import FilterPolicy

# Filter by court
filters = {
    "field": "meta.court_name",
    "operator": "==",
    "value": "Supreme Court of India"
}

results = store.get_haystack_store().filter_documents(filters=filters)

# Complex filters
filters = {
    "operator": "AND",
    "conditions": [
        {"field": "meta.court_name", "operator": "==", "value": "Supreme Court"},
        {"field": "meta.judgment_date", "operator": ">=", "value": "2020-01-01"}
    ]
}
```

## Benefits

### 1. **Production-Ready Architecture**
- Battle-tested components from Haystack ecosystem
- Optimized for performance and scalability
- Well-documented and maintained

### 2. **Extensibility**
- Easy to add new components from Haystack integrations
- Custom components follow standard interface
- Mix and match components from different providers

### 3. **Observability**
- Pipeline visualization with `.show()`
- Built-in logging at each component
- Easy debugging with step-by-step execution

### 4. **Community & Ecosystem**
- Large Haystack community
- Regular updates and improvements
- Integration with other tools (LangSmith, LangFuse, etc.)

### 5. **Backward Compatibility**
- Existing code works with minimal changes
- Gradual migration path
- No database migration required

## Troubleshooting

### Issue: Import errors

```bash
# Solution: Install Haystack dependencies
pip install haystack-ai pgvector-haystack sentence-transformers-haystack
```

### Issue: Pipeline connection errors

```python
# Check pipeline structure
print(pipeline.show())

# Verify component output types match next component input types
```

### Issue: Dual embedding retrieval not working

```python
# For metadata search, use custom retrieval (limitation of single embedding in Haystack)
# Or create separate document store for metadata embeddings
```

## Performance Considerations

### HNSW Index Configuration

```python
store = HaystackDocumentStoreWrapper()
# HNSW parameters already optimized:
# - m=16 (connections per layer)
# - ef_construction=64 (index build quality)

# For query time:
# - Haystack automatically uses ef=search_strategy parameter
```

### Batch Processing

```python
# Embed documents in batches
docs = [Document(content=text) for text in texts]
embedded_docs = embedder.embed_documents(docs)  # Batched internally

# Write in batches
store.get_haystack_store().write_documents(embedded_docs)
```

## Next Steps

1. **Review** the new component files
2. **Test** with existing data (no migration needed)
3. **Explore** Haystack integrations for additional features
4. **Build** custom components for domain-specific needs
5. **Monitor** pipeline performance and optimize as needed

## Resources

- [Haystack Documentation](https://docs.haystack.deepset.ai/)
- [PgvectorDocumentStore Reference](https://docs.haystack.deepset.ai/docs/pgvectordocumentstore)
- [Haystack Components](https://docs.haystack.deepset.ai/docs/components)
- [Haystack Tutorials](https://haystack.deepset.ai/tutorials)
