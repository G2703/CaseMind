"""
Haystack-based Ranker Components for CaseMind.
Uses TransformersSimilarityRanker for cross-encoder re-ranking.
"""

import logging
from typing import List, Optional
from haystack import Document, component
from haystack.components.rankers import TransformersSimilarityRanker

from core.config import Config

logger = logging.getLogger(__name__)


class HaystackRankerService:
    """
    Ranker service using Haystack's TransformersSimilarityRanker.
    
    Provides cross-encoder re-ranking for retrieved documents.
    """
    
    def __init__(self):
        """Initialize Haystack ranker component."""
        self.config = Config()
        self.model_name = self.config.get("RANKER_MODEL", "cross-encoder/ms-marco-MiniLM-L6-v2")
        
        # Initialize Haystack ranker
        self.ranker = TransformersSimilarityRanker(
            model=self.model_name,
            top_k=None,  # Don't limit results in ranker, handle in pipeline
            device=None  # Auto-detect GPU/CPU
        )
        self.ranker.warm_up()
        
        logger.info(f"Haystack Ranker Service initialized with model: {self.model_name}")
    
    def rank_documents(
        self,
        query: str,
        documents: List[Document],
        top_k: Optional[int] = None
    ) -> List[Document]:
        """
        Rank documents using cross-encoder.
        
        Args:
            query: Query text
            documents: List of Haystack Documents to rank
            top_k: Optional limit on number of results (None = return all)
            
        Returns:
            Ranked documents with scores
        """
        if not documents:
            return []
        
        result = self.ranker.run(
            query=query,
            documents=documents,
            top_k=top_k
        )
        
        return result['documents']


@component
class ThresholdFilterComponent:
    """
    Custom Haystack component to filter documents by score threshold.
    
    This component can be added to Haystack Pipelines to filter out
    low-scoring documents after ranking.
    """
    
    def __init__(self, threshold: float = 0.0):
        """
        Initialize threshold filter.
        
        Args:
            threshold: Minimum score to keep document
        """
        self.threshold = threshold
    
    @component.output_types(documents=List[Document])
    def run(self, documents: List[Document]) -> dict:
        """
        Filter documents by threshold.
        
        Args:
            documents: List of scored documents
            
        Returns:
            Dict with 'documents' key containing filtered list
        """
        filtered = [
            doc for doc in documents
            if hasattr(doc, 'score') and doc.score >= self.threshold
        ]
        
        logger.debug(f"Filtered {len(documents)} documents to {len(filtered)} above threshold {self.threshold}")
        
        return {"documents": filtered}


# Backward compatibility
class CrossEncoderRanker:
    """Legacy wrapper for backward compatibility."""
    
    def __init__(self, model_name: str = "cross-encoder/ms-marco-MiniLM-L6-v2"):
        self.service = HaystackRankerService()
    
    def rank(self, query: str, documents: List[Document], top_k: Optional[int] = None) -> List[Document]:
        return self.service.rank_documents(query, documents, top_k)
