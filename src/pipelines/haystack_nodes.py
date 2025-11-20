"""
Lightweight Haystack-compatible nodes built on top of existing services.
These nodes attempt to import Haystack types where available, but do not require Haystack
at runtime since they implement a minimal `run()` interface used by `similarity_pipeline`.

Nodes provided:
- `HaystackRetrieverNode` (wraps SimpleRetriever)
- `HaystackRankerNode` (wraps SimpleRanker)

They are intentionally minimal to keep integration low-risk.
"""

import logging
from typing import Any, Dict, List

from infrastructure.haystack_adapter import SimpleRetriever, SimpleRanker

logger = logging.getLogger(__name__)


class HaystackRetrieverNode:
    def __init__(self, store, embedder, embedding_field: str = "embedding_facts"):
        self.retriever = SimpleRetriever(store, embedder, embedding_field=embedding_field)

    def run(self, query: str, top_k: int = 10, exclude_id: str = None) -> Dict[str, Any]:
        return self.retriever.run(query=query, top_k=top_k, exclude_id=exclude_id)


class HaystackRankerNode:
    def __init__(self, cross_encoder):
        self.ranker = SimpleRanker(cross_encoder)

    def run(self, query: str, documents: List[Dict[str, Any]]) -> Dict[str, Any]:
        return self.ranker.run(query, documents)
