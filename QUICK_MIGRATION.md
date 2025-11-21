# Quick Migration Guide: Haystack 2.0

## ⚡ TL;DR

Your code already works with Haystack 2.0! Just install new dependencies and optionally update imports.

## Step 1: Install Dependencies

```bash
pip install -r requirements.txt
```

New packages installed:
- `haystack-ai>=2.0.0`
- `pgvector-haystack`
- `sentence-transformers-haystack`

## Step 2: Test (Optional but Recommended)

```bash
python src/scripts/test_haystack_migration.py
```

## Step 3: Use Your Code (No Changes Needed!)

Your existing code works as-is:

```python
# This still works!
from infrastructure.document_store import PGVectorDocumentStore
from services.embedding_service import EmbeddingService
from pipelines.similarity_pipeline import SimilaritySearchPipeline

store = PGVectorDocumentStore()  # Now uses Haystack internally!
embedder = EmbeddingService()     # Now uses Haystack internally!
pipeline = SimilaritySearchPipeline()  # Now uses Haystack Pipeline!
```

## Step 4: Explore New Features (Optional)

### View Migration Report
```bash
python src/scripts/haystack_migration_report.py
```

### Visualize Pipeline
```python
from pipelines.haystack_similarity_pipeline import HaystackSimilarityPipeline

pipeline = HaystackSimilarityPipeline()
print(pipeline.get_pipeline_graph())  # See the Haystack Pipeline structure!
```

### Access Haystack Components Directly
```python
from infrastructure.haystack_document_store import HaystackDocumentStoreWrapper

store = HaystackDocumentStoreWrapper()

# Get underlying Haystack store for advanced usage
haystack_store = store.get_haystack_store()

# Use with any Haystack component
from haystack_integrations.components.retrievers.pgvector import PgvectorEmbeddingRetriever
retriever = PgvectorEmbeddingRetriever(document_store=haystack_store)
```

## What Changed?

### Before
- Custom document store with raw SQL
- Direct model usage
- Manual pipeline orchestration

### After
- ✅ Haystack PgvectorDocumentStore (HNSW indexing)
- ✅ Haystack SentenceTransformers components
- ✅ Haystack Pipeline with automatic optimization
- ✅ **Same interface - backward compatible!**

## Benefits You Get

✅ **Better Performance**: Optimized HNSW indexing  
✅ **Extensibility**: Easy to add 50+ Haystack integrations  
✅ **Observability**: Pipeline visualization and logging  
✅ **Production-Ready**: Battle-tested components  
✅ **Future-Proof**: Active Haystack community and updates  

## Common Questions

**Q: Do I need to migrate my database?**  
A: No! Existing data works perfectly.

**Q: Will my code break?**  
A: No! Full backward compatibility maintained.

**Q: Do I need to change my imports?**  
A: No! Old imports automatically use new Haystack components.

**Q: Can I use Haystack features directly?**  
A: Yes! Use `get_haystack_store()` or import Haystack components directly.

**Q: What if something breaks?**  
A: Run the test script to identify issues. All components have fallback mechanisms.

## Getting Help

- 📖 **Full Guide**: [HAYSTACK_INTEGRATION.md](HAYSTACK_INTEGRATION.md)
- 📝 **Summary**: [REFACTORING_SUMMARY.md](REFACTORING_SUMMARY.md)
- 🔬 **Test**: `python src/scripts/test_haystack_migration.py`
- 📊 **Report**: `python src/scripts/haystack_migration_report.py`
- 🌐 **Haystack Docs**: https://docs.haystack.deepset.ai/

## That's It!

Your code already uses Haystack 2.0. Enjoy the benefits! 🎉

---

**Next Steps**:
1. ✅ Install dependencies
2. ✅ Test (optional)
3. ✅ Use your existing code (it just works!)
4. 🚀 Explore new Haystack features when ready
