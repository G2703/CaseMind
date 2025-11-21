"""
Haystack-based Similarity Search Pipeline for CaseMind.
Uses native Haystack Pipeline with proper components.
"""

import logging
from typing import Optional
from pathlib import Path
from haystack import Pipeline, Document
from haystack_integrations.components.retrievers.pgvector import PgvectorEmbeddingRetriever

from core.models import SimilaritySearchResult, SimilarCase, IngestResult, ProcessingStatus
from core.config import Config
from pipelines.ingestion_pipeline import DataIngestionPipeline
from infrastructure.haystack_document_store import HaystackDocumentStoreWrapper
from infrastructure.haystack_document_converter import HaystackDocumentConverter
from services.haystack_embedding_service import HaystackEmbeddingService
from services.haystack_ranker_service import HaystackRankerService, ThresholdFilterComponent

logger = logging.getLogger(__name__)


class HaystackSimilarityPipeline:
    """
    Haystack-based similarity search pipeline.
    
    Architecture:
    1. Ingestion: PDF → Metadata → Facts → Embeddings → DocumentStore
    2. Retrieval Pipeline:
       - TextEmbedder (query → embedding)
       - PgvectorEmbeddingRetriever (embedding → candidate docs)
       - TransformersSimilarityRanker (re-rank with cross-encoder)
       - ThresholdFilter (filter low scores)
    """
    
    def __init__(self, ingestion_pipeline: Optional[DataIngestionPipeline] = None):
        """
        Initialize Haystack-based similarity pipeline.
        
        Args:
            ingestion_pipeline: Optional existing ingestion pipeline to reuse
        """
        self.config = Config()
        self.ingestion_pipeline = ingestion_pipeline or DataIngestionPipeline()
        
        # Initialize Haystack components
        self.document_store = HaystackDocumentStoreWrapper()
        self.embedder = HaystackEmbeddingService()
        self.ranker = HaystackRankerService()
        self.converter = HaystackDocumentConverter()
        
        # Get configuration
        self.top_k = self.config.get("TOP_K_SIMILAR_CASES", 5)
        self.threshold = self.config.get("CROSS_ENCODER_THRESHOLD", 0.0)
        
        # Build retrieval pipeline
        self._build_retrieval_pipeline()
        
        logger.info("Haystack Similarity Pipeline initialized")
    
    def _build_retrieval_pipeline(self):
        """Build Haystack Pipeline for retrieval, ranking, and filtering."""
        
        # Create retriever component
        self.retriever_facts = PgvectorEmbeddingRetriever(
            document_store=self.document_store.get_haystack_store(),
            top_k=self.top_k  # Retrieve 3x for re-ranking
        )
        
        # Create filter component
        self.threshold_filter = ThresholdFilterComponent(threshold=self.threshold)
        
        # Build pipeline
        self.retrieval_pipeline = Pipeline()
        
        # Add components to pipeline
        self.retrieval_pipeline.add_component("retriever", self.retriever_facts)
        self.retrieval_pipeline.add_component("ranker", self.ranker.ranker)
        self.retrieval_pipeline.add_component("threshold_filter", self.threshold_filter)
        
        # Connect components
        self.retrieval_pipeline.connect("retriever.documents", "ranker.documents")
        self.retrieval_pipeline.connect("ranker.documents", "threshold_filter.documents")
        
        logger.debug("Haystack retrieval pipeline built: retriever → ranker → threshold_filter")
    
    async def run_full_pipeline(
        self,
        file_path: Path,
        use_metadata_query: bool = False,
        metadata_query: Optional[str] = None
    ) -> SimilaritySearchResult:
        """
        Run complete similarity search pipeline using Haystack components.
        
        Args:
            file_path: Path to query PDF file
            use_metadata_query: If True, search by metadata instead of facts
            metadata_query: Custom metadata query string (optional)
            
        Returns:
            SimilaritySearchResult with similar cases
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        logger.info(f"Starting Haystack similarity search for: {file_path.name}")
        
        # Phase 1: Ingest query document
        logger.info("Phase 1: Ingesting query document")
        ingest_result = await self.ingestion_pipeline.ingest_pdf(file_path)
        
        if ingest_result.status == ProcessingStatus.FAILED:
            return SimilaritySearchResult(
                query_file=str(file_path),
                input_case=None,
                similar_cases=[],
                total_above_threshold=0,
                search_mode="facts" if not use_metadata_query else "metadata",
                error_message=ingest_result.error_message
            )
        
        # Phase 2: Prepare query for retrieval
        logger.info("Phase 2: Retrieving similar cases using Haystack Pipeline")
        
        if use_metadata_query and metadata_query:
            search_text = metadata_query
        elif use_metadata_query:
            # Build metadata query from case metadata
            meta = ingest_result.metadata
            search_text = f"{meta.sections_invoked} {meta.court_name} {meta.case_title}"
        else:
            # Use facts summary for query
            search_text = ingest_result.facts_summary
        
        # Get query embedding
        query_embedding = self.embedder.embed_text(search_text)
        
        # Phase 3: Run Haystack retrieval pipeline
        try:
            pipeline_result = self.retrieval_pipeline.run({
                "retriever": {
                    "query_embedding": query_embedding.tolist(),
                    "filters": {
                        "field": "id",
                        "operator": "!=",
                        "value": ingest_result.case_id
                    }
                },
                "ranker": {
                    "query": search_text,
                    "top_k": self.top_k
                }
            })
            
            filtered_documents = pipeline_result["threshold_filter"]["documents"]
            
        except Exception as e:
            logger.error(f"Haystack pipeline execution failed: {e}")
            # Fallback to direct retrieval
            filtered_documents = self._fallback_retrieval(
                query_embedding,
                search_text,
                ingest_result.case_id
            )
        
        # Phase 4: Convert Haystack Documents to SimilarCase objects
        logger.info(f"Phase 4: Processing {len(filtered_documents)} similar cases")
        
        similar_cases = []
        for doc in filtered_documents:
            meta = doc.meta or {}
            
            similar_case = SimilarCase(
                document_id=doc.id,
                case_title=meta.get('case_title', 'Unknown'),
                court_name=meta.get('court_name', 'Unknown'),
                judgment_date=meta.get('judgment_date', 'Unknown'),
                facts_summary=doc.content[:500] + "..." if len(doc.content) > 500 else doc.content,
                cosine_similarity=float(meta.get('vector_similarity_score', 0.0)),
                cross_encoder_score=float(doc.score) if hasattr(doc, 'score') else 0.0,
                sections_invoked=meta.get('sections_invoked', [])
            )
            similar_cases.append(similar_case)
        
        # Create result
        result = SimilaritySearchResult(
            query_file=str(file_path),
            input_case=ingest_result,
            similar_cases=similar_cases,
            total_above_threshold=len(similar_cases),
            search_mode="metadata" if use_metadata_query else "facts",
            error_message=None
        )
        
        logger.info(f"Haystack similarity search completed: {len(similar_cases)} cases above threshold")
        return result
    
    def _fallback_retrieval(
        self,
        query_embedding,
        search_text: str,
        exclude_id: str
    ) -> list:
        """Fallback retrieval if pipeline fails."""
        logger.warning("Using fallback retrieval method")
        
        try:
            # Direct document store query
            results = self.document_store.query_by_embedding(
                embedding=query_embedding,
                top_k=self.top_k * 3,
                embedding_field="embedding_facts",
                exclude_id=exclude_id
            )
            
            # Convert to Haystack Documents for ranking
            docs = []
            for result in results:
                doc = Document(
                    id=result['id'],
                    content=result['content'],
                    meta=result['meta']
                )
                docs.append(doc)
            
            # Rank with Haystack ranker
            ranked_docs = self.ranker.rank_documents(search_text, docs, top_k=self.top_k)
            
            # Filter by threshold
            filtered = [d for d in ranked_docs if hasattr(d, 'score') and d.score >= self.threshold]
            
            return filtered
            
        except Exception as e:
            logger.error(f"Fallback retrieval also failed: {e}")
            return []
    
    def get_pipeline_graph(self) -> str:
        """Get visual representation of Haystack pipeline."""
        return self.retrieval_pipeline.show()


# Backward compatibility alias
SimilaritySearchPipeline = HaystackSimilarityPipeline
