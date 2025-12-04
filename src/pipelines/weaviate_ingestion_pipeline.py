"""
Weaviate Ingestion Pipeline for CaseMind using Haystack 2.x.
Factory function to build and return Haystack pipeline directly.

Pipeline stages:
1. PDF → Markdown extraction (PDFToMarkdownConverter)
2. Markdown normalization & storage (MarkdownNormalizer)
3. Text chunking (TextChunker)
4a. Summary extraction (SummaryExtractor)
4b. Template fact extraction (TemplateFactsExtractor)
5. Batch embedding generation (EmbeddingGenerator)
6. Weaviate batch upsert (WeaviateWriter)
"""

import sys
import os
from pathlib import Path
from typing import Optional

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from haystack import Pipeline

from src.core.config import Config
from src.components.pdf_to_markdown import PDFToMarkdownConverter
from src.components.markdown_normalizer import MarkdownNormalizer
from src.components.text_chunker import TextChunker
from src.components.summary_extractor import SummaryExtractor
from src.components.template_facts_extractor import TemplateFactsExtractor
from src.components.embedding_generator import EmbeddingGenerator
from src.components.weaviate_writer import WeaviateWriter
from src.utils.logger import get_logger

logger = get_logger(__name__)


def create_weaviate_ingestion_pipeline(
    config: Optional[Config] = None,
    skip_existing: bool = True
) -> Pipeline:
    """
    Build Haystack pipeline for legal document ingestion.
    
    Args:
        config: Optional Config instance (defaults to Config())
        skip_existing: Skip files already ingested (default: True)
    
    Returns:
        Configured Haystack Pipeline ready to run
    """
    config = config or Config()
    pipeline = Pipeline()
    
    # Stage 1: PDF to Markdown
    pipeline.add_component("pdf_converter", PDFToMarkdownConverter())
    
    # Stage 2: Markdown Normalization & Storage
    pipeline.add_component("markdown_normalizer", MarkdownNormalizer())
    
    # Stage 3: Text Chunking
    pipeline.add_component("text_chunker", TextChunker())
    
    # Stage 4a: Summary Extraction
    pipeline.add_component("summary_extractor", SummaryExtractor(config=config))
    
    # Stage 4b: Template Facts Extraction
    pipeline.add_component("template_facts_extractor", TemplateFactsExtractor(config=config))
    
    # Stage 5: Embedding Generation
    pipeline.add_component("embedding_generator", EmbeddingGenerator())
    
    # Stage 6: Weaviate Writer
    pipeline.add_component("weaviate_writer", WeaviateWriter(skip_existing=skip_existing))
    
    # Connect components
    pipeline.connect("pdf_converter.documents", "markdown_normalizer.documents")
    pipeline.connect("markdown_normalizer.documents", "text_chunker.documents")
    pipeline.connect("text_chunker.documents", "summary_extractor.documents")
    pipeline.connect("text_chunker.chunks", "summary_extractor.chunks")
    pipeline.connect("summary_extractor.documents", "template_facts_extractor.documents")
    pipeline.connect("summary_extractor.chunks", "template_facts_extractor.chunks")
    pipeline.connect("summary_extractor.extractions", "template_facts_extractor.extractions")
    pipeline.connect("template_facts_extractor.documents", "embedding_generator.documents")
    pipeline.connect("template_facts_extractor.chunks", "embedding_generator.chunks")
    pipeline.connect("template_facts_extractor.extractions", "embedding_generator.extractions")
    pipeline.connect("template_facts_extractor.sections", "embedding_generator.sections")
    pipeline.connect("embedding_generator.documents", "weaviate_writer.documents")
    pipeline.connect("embedding_generator.chunks", "weaviate_writer.chunks")
    pipeline.connect("embedding_generator.extractions", "weaviate_writer.extractions")
    pipeline.connect("embedding_generator.sections", "weaviate_writer.sections")
    
    logger.info("Haystack pipeline built with 7 components")
    return pipeline
