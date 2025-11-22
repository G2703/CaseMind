"""
Pure Haystack-based Similarity Search Pipeline.
Uses only native Haystack components - no wrappers.
"""

import logging
from pathlib import Path
from typing import Optional, List
from datetime import datetime

from haystack import Pipeline, Document
from haystack.components.embedders import SentenceTransformersTextEmbedder
from haystack.components.rankers import TransformersSimilarityRanker
from haystack_integrations.document_stores.pgvector import PgvectorDocumentStore

from core.config import Config
from core.models import SimilaritySearchResult, SimilarCase, IngestResult, ProcessingStatus
from pipelines.haystack_ingestion_pipeline import HaystackIngestionPipeline
from pipelines.haystack_custom_nodes import ThresholdFilterNode, FactsEmbeddingRetriever

logger = logging.getLogger(__name__)


class PureHaystackSimilarityPipeline:
    """
    Pure Haystack similarity search pipeline using native components.
    
    Pipeline Flow:
    1. Query PDF → HaystackIngestionPipeline → Embedding
    2. Query Embedding → PgvectorEmbeddingRetriever (cosine similarity)
    3. Retrieved Docs → TransformersSimilarityRanker (cross-encoder)
    4. Ranked Docs → ThresholdFilterNode (filter by score)
    5. Filtered Docs → Format as SimilarCase objects
    """
    
    def __init__(self):
        """Initialize pure Haystack similarity pipeline."""
        self.config = Config()
        
        # Initialize ingestion pipeline for query documents
        self.ingestion_pipeline = HaystackIngestionPipeline()
        
        # Get document store from ingestion pipeline (same instance)
        self.document_store = self.ingestion_pipeline.document_store
        
        # Configuration
        self.top_k_retrieval = self.config.top_k   # Retrieve 3x for reranking
        self.top_k_final = self.config.top_k
        self.threshold = self.config.cross_encoder_threshold
        
        # Build retrieval pipeline
        self._build_retrieval_pipeline()
        
        logger.info("PureHaystackSimilarityPipeline initialized")
    
    def _build_retrieval_pipeline(self):
        """Build Haystack pipeline for similarity search using facts embeddings."""
        
        # 1. Text Embedder (for query)
        text_embedder = SentenceTransformersTextEmbedder(
            model="sentence-transformers/all-mpnet-base-v2",
            progress_bar=False
        )
        
        # 2. Facts Embedding Retriever (searches on 'embedding' column with facts)
        retriever = FactsEmbeddingRetriever(
            document_store=self.document_store,
            top_k=self.top_k_retrieval
        )
        
        # 3. Reranker (cross-encoder)
        ranker = TransformersSimilarityRanker(
            model="cross-encoder/ms-marco-MiniLM-L-6-v2",
            top_k=self.top_k_final
        )
        
        # 4. Threshold Filter
        threshold_filter = ThresholdFilterNode(threshold=self.threshold)
        
        # Build pipeline
        self.retrieval_pipeline = Pipeline()
        
        # Add components
        self.retrieval_pipeline.add_component("text_embedder", text_embedder)
        self.retrieval_pipeline.add_component("retriever", retriever)
        self.retrieval_pipeline.add_component("ranker", ranker)
        self.retrieval_pipeline.add_component("threshold_filter", threshold_filter)
        
        # Connect components
        self.retrieval_pipeline.connect("text_embedder.embedding", "retriever.query_embedding")
        self.retrieval_pipeline.connect("retriever.documents", "ranker.documents")
        self.retrieval_pipeline.connect("ranker.documents", "threshold_filter.documents")
        
        logger.info("Retrieval pipeline built: text_embedder → facts_retriever → ranker → threshold_filter")
    
    async def search_similar(
        self,
        file_path: Path,
        use_metadata_query: bool = False
    ) -> SimilaritySearchResult:
        """
        Search for similar cases using pure Haystack pipeline.
        
        Args:
            file_path: Path to query PDF file
            use_metadata_query: If True, search by metadata instead of facts
            
        Returns:
            SimilaritySearchResult with similar cases
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        logger.info(f"Starting similarity search for: {file_path.name}")
        
        # Phase 1: Ingest query document
        logger.info("Phase 1: Ingesting query document")
        ingest_result = await self.ingestion_pipeline.ingest_single(file_path)
        
        # Handle failed ingestion
        if ingest_result.status == ProcessingStatus.FAILED:
            return SimilaritySearchResult(
                query_file=str(file_path),
                input_case=None,
                similar_cases=[],
                total_above_threshold=0,
                search_mode="facts" if not use_metadata_query else "metadata",
                error_message=ingest_result.error_message
            )
        
        # Log if document was a duplicate (but continue with similarity search)
        if ingest_result.status == ProcessingStatus.SKIPPED_DUPLICATE:
            logger.info("Query document is a duplicate, using existing data for similarity search")
        
        # Phase 2: Prepare query text
        logger.info("Phase 2: Preparing query for retrieval")
        
        # Check if metadata is available
        if ingest_result.metadata is None:
            logger.error("Metadata is None, cannot build query")
            return SimilaritySearchResult(
                query_file=str(file_path),
                input_case=ingest_result,
                similar_cases=[],
                total_above_threshold=0,
                search_mode="facts" if not use_metadata_query else "metadata",
                error_message="No metadata available for query"
            )
        
        if use_metadata_query:
            # Build metadata query from case metadata
            meta = ingest_result.metadata
            sections = ' '.join(meta.sections_invoked) if meta.sections_invoked else ''
            search_text = f"{sections} {meta.court_name} {meta.case_title}"
        else:
            # Use facts summary for query (fallback to metadata if no facts)
            search_text = ingest_result.facts_summary
            if not search_text or len(search_text.strip()) == 0:
                logger.warning("No facts summary available, using metadata for search")
                meta = ingest_result.metadata
                sections = ' '.join(meta.sections_invoked) if meta.sections_invoked else ''
                search_text = f"{sections} {meta.court_name} {meta.case_title}"
        
        logger.info(f"Query text length: {len(search_text)} characters")
        
        # Phase 3: Run Haystack retrieval pipeline
        logger.info("Phase 3: Running Haystack retrieval pipeline")
        
        try:
            # Build filters to exclude query document
            filters = None
            if ingest_result.case_id:
                filters = {
                    "field": "id",
                    "operator": "!=",
                    "value": ingest_result.document_id
                }
            
            # Run pipeline
            pipeline_result = self.retrieval_pipeline.run({
                "text_embedder": {"text": search_text},
                "retriever": {"filters": filters},
                "ranker": {"query": search_text}
            })
            
            # Get filtered documents
            filtered_documents = pipeline_result["threshold_filter"]["documents"]
            
            logger.info(f"Retrieved {len(filtered_documents)} similar cases above threshold")
            
        except Exception as e:
            logger.error(f"Pipeline execution failed: {e}")
            return SimilaritySearchResult(
                query_file=str(file_path),
                input_case=ingest_result,
                similar_cases=[],
                total_above_threshold=0,
                search_mode="facts" if not use_metadata_query else "metadata",
                error_message=f"Retrieval failed: {str(e)}"
            )
        
        # Phase 4: Convert to SimilarCase objects
        logger.info("Phase 4: Formatting results")
        
        similar_cases = []
        for doc in filtered_documents:
            meta = doc.meta or {}
            
            # Extract scores
            cross_encoder_score = float(doc.score) if hasattr(doc, 'score') else 0.0
            
            # Cosine similarity is stored during retrieval
            # PgvectorEmbeddingRetriever adds it to meta
            cosine_similarity = float(meta.get('score', 0.0))
            
            similar_case = SimilarCase(
                document_id=doc.id,
                case_title=meta.get('case_title', 'Unknown'),
                court_name=meta.get('court_name', 'Unknown'),
                judgment_date=meta.get('judgment_date', 'Unknown'),
                facts_summary=doc.content[:500] + "..." if len(doc.content) > 500 else doc.content,
                cosine_similarity=cosine_similarity,
                cross_encoder_score=cross_encoder_score,
                sections_invoked=meta.get('sections_invoked', [])
            )
            similar_cases.append(similar_case)
        
        # Create result
        result = SimilaritySearchResult(
            query_file=str(file_path),
            input_case=ingest_result,
            similar_cases=similar_cases,
            total_above_threshold=len(similar_cases),
            search_mode="metadata" if use_metadata_query else "metadata",
            error_message=None
        )
        
        logger.info(f"Similarity search completed: {len(similar_cases)} cases found")
        return result
    
    def visualize_pipeline(self) -> str:
        """Get visual representation of the retrieval pipeline."""
        return self.retrieval_pipeline.show()
