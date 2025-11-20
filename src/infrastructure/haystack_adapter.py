"""
Adapter utilities to integrate existing PGVectorDocumentStore with Haystack pipelines.
This module attempts to import Haystack types but degrades gracefully if Haystack is not installed.

It provides:
- `to_haystack_document(dict_row)` to convert DB rows to Haystack `Document` objects (if available)
- `build_retriever(store, embedder, embedding_field)` that returns a simple retriever object
  compatible with a Haystack-like `run(query, params)` interface.

The goal is minimal, low-risk integration: if Haystack is available the `similarity_pipeline`
will wire up a Pipeline; otherwise it falls back to existing logic.
"""

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

try:
    # Haystack v1/v2 Document import locations may vary; try common paths
    try:
        from haystack import Document as HaystackDocument
    except Exception:
        from haystack.schema import Document as HaystackDocument
    _HAYSTACK_AVAILABLE = True
    logger.debug("Haystack detected: adapter will produce haystack Documents")
except Exception:
    HaystackDocument = None
    _HAYSTACK_AVAILABLE = False
    logger.debug("Haystack not available: adapter will return plain dicts")


def to_haystack_document(row: Dict[str, Any]):
    """Convert a database row (dict) to a Haystack Document if available; otherwise return dict.

    Args:
        row: dict with keys like `id`, `content`, `meta`, `similarity_score`, etc.

    Returns:
        Haystack Document or dict fallback
    """
    if _HAYSTACK_AVAILABLE and HaystackDocument is not None:
        # Haystack Document typically accepts content and meta
        return HaystackDocument(content=row.get("content", ""), metadata=row.get("meta", {}))
    # Fallback
    return row


class SimpleRetriever:
    """
    Minimal retriever wrapper that uses the existing `PGVectorDocumentStore` interface.

    The class exposes a `run()` method similar to Haystack nodes so it can be plugged
    into a Pipeline-like orchestration. It does not inherit from Haystack's base classes
    to avoid tight coupling; rather, it implements a compatible `run(query, params)`.
    """

    def __init__(self, store, embedder, embedding_field: str = "embedding_facts"):
        self.store = store
        self.embedder = embedder
        self.embedding_field = embedding_field

    def run(self, query: str, top_k: int = 10, exclude_id: Optional[str] = None) -> Dict[str, Any]:
        """Embed the query, call the store, and return a dict with 'documents' key.

        Returns:
            { 'documents': [Document|dict, ...] }
        """
        emb = self.embedder.embed_text(query)
        results = self.store.query_by_embedding(emb, top_k=top_k, embedding_field=self.embedding_field, exclude_id=exclude_id)
        docs = [to_haystack_document(r) for r in results]
        return {"documents": docs}


class SimpleRanker:
    """
    Minimal ranker wrapper that uses a Cross-Encoder model to score candidate documents.

    Exposes `run(query, documents)` and returns documents annotated with `score`.
    """

    def __init__(self, cross_encoder):
        self.cross_encoder = cross_encoder

    def run(self, query: str, documents: List[Dict[str, Any]]) -> Dict[str, Any]:
        pairs = [(query, (d.content if hasattr(d, 'content') else d.get('content', ''))) for d in documents]
        scores = self.cross_encoder.predict(pairs)
        # Attach score
        out_docs = []
        for doc, s in zip(documents, scores):
            if hasattr(doc, 'metadata'):
                # Haystack Document
                if isinstance(doc.metadata, dict):
                    doc.metadata['cross_encoder_score'] = float(s)
                else:
                    try:
                        doc.metadata = dict(doc.metadata)
                        doc.metadata['cross_encoder_score'] = float(s)
                    except Exception:
                        pass
            elif isinstance(doc, dict):
                doc['cross_encoder_score'] = float(s)
            out_docs.append(doc)
        return {"documents": out_docs}
