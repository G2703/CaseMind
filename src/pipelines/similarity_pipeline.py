"""
Similarity search pipeline for finding similar legal cases.
Includes ingestion, retrieval, re-ranking, and threshold filtering.
"""

import logging
from typing import List
from pathlib import Path
from sentence_transformers import CrossEncoder

from core.models import (
    SimilaritySearchResult, SimilarCase, IngestResult, ProcessingStatus
)
from core.config import Config
from pipelines.ingestion_pipeline import DataIngestionPipeline
from infrastructure.document_store import PGVectorDocumentStore
from services.embedding_service import EmbeddingService
from pipelines.haystack_nodes import HaystackRetrieverNode, HaystackRankerNode

logger = logging.getLogger(__name__)


class SimilaritySearchPipeline:
    """
    Orchestrates similarity search workflow (Steps 1-17).
    Combines ingestion, retrieval, re-ranking, and filtering.
    """
    
    def __init__(self, ingestion_pipeline: DataIngestionPipeline = None):
        """Initialize pipeline components.
        
        Args:
            ingestion_pipeline: Optional existing ingestion pipeline to reuse (avoids duplicate initialization)
        """
        self.config = Config()
        self.ingestion_pipeline = ingestion_pipeline or DataIngestionPipeline()
        self.store = PGVectorDocumentStore()
        self.embedder = EmbeddingService()
        
        # Initialize cross-encoder for re-ranking (Step 14)
        ranker_model = self.config.get("RANKER_MODEL", "cross-encoder/ms-marco-MiniLM-L6-v2")
        logger.info(f"Loading cross-encoder model: {ranker_model}")
        self.cross_encoder = CrossEncoder(ranker_model)
        
        # Get configuration
        self.top_k = self.config.get("TOP_K_SIMILAR_CASES", 3)
        self.threshold = self.config.get("CROSS_ENCODER_THRESHOLD", 0.0)
        # Try to initialize lightweight Haystack-compatible nodes (adapter pattern)
        try:
            # Use facts embedding by default for retriever
            self.haystack_retriever = HaystackRetrieverNode(self.store, self.embedder, embedding_field="embedding_facts")
            self.haystack_ranker = HaystackRankerNode(self.cross_encoder)
            self.use_haystack_nodes = True
            logger.info("Haystack-compatible nodes initialized and will be used when possible")
        except Exception as e:
            self.haystack_retriever = None
            self.haystack_ranker = None
            self.use_haystack_nodes = False
            logger.debug(f"Haystack-compatible nodes unavailable: {e}")

        logger.info("Similarity search pipeline initialized")
    
    async def run_full_pipeline(
        self, 
        file_path: Path,
        use_metadata_query: bool = False,
        metadata_query: str = None
    ) -> SimilaritySearchResult:
        """
        Run complete similarity search pipeline (Steps 1-17).
        
        Args:
            file_path: Path to query PDF file
            use_metadata_query: If True, search by metadata instead of facts
            metadata_query: Custom metadata query string (optional)
            
        Returns:
            SimilaritySearchResult with similar cases
        """
        file_path = Path(file_path)
        logger.info(f"Running full similarity pipeline for: {file_path.name}")
        
        # ========== PHASE 1: INGEST QUERY CASE (Steps 1-11) ==========
        logger.info("Phase 1: Ingesting query case")
        ingest_result = await self.ingestion_pipeline.ingest_single(file_path)
        
        if ingest_result.status == ProcessingStatus.FAILED:
            logger.error(f"Ingestion failed: {ingest_result.error_message}")
            return SimilaritySearchResult(
                input_case=ingest_result,
                similar_cases=[],
                total_retrieved=0,
                total_above_threshold=0
            )
        
        # ========== PHASE 2: RETRIEVE SIMILAR CASES (Steps 12-13) ==========
        logger.info("Phase 2: Retrieving similar cases")
        
        # Select embedding type
        if use_metadata_query and metadata_query:
            # Custom metadata query
            query_embedding = self.embedder.embed_query(metadata_query)
            embedding_field = 'embedding_metadata'
            search_text = metadata_query
        elif use_metadata_query:
            # Use query case's metadata embedding
            query_embedding = ingest_result.embedding_metadata
            embedding_field = 'embedding_metadata'
            search_text = ingest_result.metadata.to_metadata_text()
        else:
            # Use query case's facts embedding (default)
            query_embedding = ingest_result.embedding_facts
            embedding_field = 'embedding_facts'
            search_text = ingest_result.facts_summary
        
        # Retrieve top-k candidates (Step 13)
        # Request more candidates for re-ranking (3x top_k)
        retrieval_k = self.top_k * 3

        # If Haystack-compatible nodes were initialized, use them (non-invasive integration)
        if self.use_haystack_nodes:
            # Temporarily set retriever's embedding field if metadata search requested
            try:
                if embedding_field == 'embedding_metadata':
                    # Re-create or adjust retriever for metadata field
                    self.haystack_retriever = HaystackRetrieverNode(self.store, self.embedder, embedding_field="embedding_metadata")
                candidates_result = self.haystack_retriever.run(search_text, top_k=retrieval_k, exclude_id=ingest_result.case_id)
                raw_docs = candidates_result.get('documents', [])
                # If ranker node exists, run re-ranking now to attach cross-encoder scores
                if self.haystack_ranker is not None:
                    ranked_result = self.haystack_ranker.run(search_text, raw_docs)
                    raw_docs = ranked_result.get('documents', raw_docs)

                # Convert raw_docs (haystack Documents or dicts) to SimilarCase objects
                candidates = []
                for doc in raw_docs:
                    # doc may be haystack Document object or a dict from adapter
                    if hasattr(doc, 'metadata'):
                        meta = doc.metadata or {}
                        content = getattr(doc, 'content', '')
                        cross_score = float(meta.get('cross_encoder_score', 0.0))
                    elif isinstance(doc, dict):
                        meta = doc.get('meta', {})
                        content = doc.get('content', '')
                        cross_score = float(doc.get('cross_encoder_score', 0.0))
                    else:
                        meta = {}
                        content = str(doc)
                        cross_score = 0.0

                    similar_case = SimilarCase(
                        document_id=meta.get('case_id', meta.get('id', 'unknown')),
                        case_title=meta.get('case_title', 'Unknown'),
                        court_name=meta.get('court_name', 'Unknown'),
                        judgment_date=meta.get('judgment_date', 'Unknown'),
                        facts_summary=content,
                        cosine_similarity=float(meta.get('vector_similarity_score', 0.0)),
                        cross_encoder_score=cross_score,
                        sections_invoked=meta.get('sections_invoked', [])
                    )
                    candidates.append(similar_case)
            except Exception as e:
                logger.warning(f"Haystack nodes failed, falling back to native retrieval: {e}")
                candidates = self.retrieve_similar(
                    query_embedding,
                    top_k=retrieval_k,
                    embedding_field=embedding_field,
                    exclude_case_id=ingest_result.case_id
                )
        else:
            candidates = self.retrieve_similar(
                query_embedding,
                top_k=retrieval_k,
                embedding_field=embedding_field,
                exclude_case_id=ingest_result.case_id  # Exclude query case
            )
        
        logger.info(f"Retrieved {len(candidates)} candidate cases")
        
        if not candidates:
            logger.info("No similar cases found")
            return SimilaritySearchResult(
                input_case=ingest_result,
                similar_cases=[],
                total_retrieved=0,
                total_above_threshold=0
            )
        
        # ========== PHASE 3: RE-RANK WITH CROSS-ENCODER (Step 14-15) ==========
        logger.info("Phase 3: Re-ranking with cross-encoder")
        
        reranked_cases = self.rerank_results(search_text, candidates)
        
        # ========== PHASE 4: FILTER BY THRESHOLD (Step 16-17) ==========
        logger.info("Phase 4: Filtering by threshold")
        
        filtered_cases = self.filter_by_threshold(reranked_cases, self.threshold)
        
        # Remove near-duplicates (similarity >= 0.99)
        final_cases = [
            case for case in filtered_cases
            if case.cross_encoder_score < 0.99
        ]
        
        # Limit to top_k
        final_cases = final_cases[:self.top_k]
        
        logger.info(f"Found {len(final_cases)} similar cases after filtering")
        
        return SimilaritySearchResult(
            input_case=ingest_result,
            similar_cases=final_cases,
            total_retrieved=len(candidates),
            total_above_threshold=len(final_cases)
        )
    
    def retrieve_similar(
        self, 
        query_embedding: List[float],
        top_k: int = 10,
        embedding_field: str = 'embedding_facts',
        exclude_case_id: str = None
    ) -> List[SimilarCase]:
        """
        Retrieve similar cases by vector similarity (Step 13).
        
        Args:
            query_embedding: Query vector
            top_k: Number of results
            embedding_field: Which embedding to use ('embedding_facts' or 'embedding_metadata')
            exclude_case_id: Case ID to exclude (query case)
            
        Returns:
            List of SimilarCase objects
        """
        logger.info(f"Querying {embedding_field} with top_k={top_k}")
        
        # Convert query_embedding to numpy array if it's a list
        import numpy as np
        if isinstance(query_embedding, list):
            query_embedding = np.array(query_embedding)
        
        # Query document store
        results = self.store.query_by_embedding(
            embedding=query_embedding,
            top_k=top_k,
            embedding_field=embedding_field,
            exclude_id=exclude_case_id
        )
        
        # Convert to SimilarCase objects
        similar_cases = []
        for doc in results:
            case_id = doc['id']
            
            # Skip query case
            if exclude_case_id and case_id == exclude_case_id:
                continue
            
            # Extract metadata
            meta = doc.get('meta', {})
            
            similar_case = SimilarCase(
                document_id=case_id,
                case_title=meta.get('case_title', 'Unknown'),
                court_name=meta.get('court_name', 'Unknown'),
                judgment_date=meta.get('judgment_date', 'Unknown'),
                facts_summary=doc.get('content', ''),
                cosine_similarity=doc.get('score', 0.0),
                cross_encoder_score=0.0,  # Will be updated in re-ranking
                sections_invoked=meta.get('sections_invoked', [])
            )
            
            similar_cases.append(similar_case)
        
        return similar_cases
    
    def rerank_results(
        self, 
        query_text: str, 
        candidates: List[SimilarCase]
    ) -> List[SimilarCase]:
        """
        Re-rank results using cross-encoder (Step 14-15).
        
        Args:
            query_text: Query text (facts or metadata)
            candidates: List of candidate cases
            
        Returns:
            Re-ranked list of SimilarCase objects
        """
        if not candidates:
            return []
        
        # Prepare pairs for cross-encoder
        pairs = [
            (query_text, case.facts_summary)
            for case in candidates
        ]
        
        # Get cross-encoder scores
        logger.info(f"Re-ranking {len(pairs)} candidates with cross-encoder")
        scores = self.cross_encoder.predict(pairs)
        
        # Update scores
        for case, score in zip(candidates, scores):
            case.cross_encoder_score = float(score)
        
        # Sort by cross-encoder score (descending)
        reranked = sorted(
            candidates, 
            key=lambda x: x.cross_encoder_score, 
            reverse=True
        )
        
        return reranked
    
    def filter_by_threshold(
        self, 
        cases: List[SimilarCase],
        threshold: float = 0.0
    ) -> List[SimilarCase]:
        """
        Filter cases by cross-encoder threshold (Step 16-17).
        
        Args:
            cases: List of cases
            threshold: Minimum cross-encoder score
            
        Returns:
            Filtered list
        """
        filtered = [
            case for case in cases
            if case.cross_encoder_score >= threshold
        ]
        
        logger.info(f"Filtered {len(cases)} → {len(filtered)} cases "
                   f"(threshold={threshold})")
        
        return filtered
