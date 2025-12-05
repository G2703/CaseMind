"""
Extraction Stage - Rate-limited LLM extraction.
Uses OpenAI client pool with strict rate limiting.
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import json

from haystack import Document
from src.services.extraction_service import ExtractionService
from src.core.pools import OpenAIClientPool
from src.core.config import Config
from src.components.text_chunker import TextChunker

logger = logging.getLogger(__name__)


@dataclass
class ExtractionResult:
    """Result from extraction processing."""
    file_id: str
    original_filename: str
    document: Optional[Document] = None
    chunks: Optional[List[Dict]] = None
    extraction: Optional[Dict] = None
    sections: Optional[List[Dict]] = None
    template_facts: Optional[Dict] = None
    error: Optional[str] = None
    success: bool = False


class ExtractionStage:
    """
    Stage 2: Rate-limited LLM extraction.
    Extracts metadata, facts, and sections using OpenAI API with rate limiting.
    """
    
    def __init__(self, config: Optional[Config] = None):
        """
        Initialize extraction stage.
        
        Args:
            config: Configuration instance
        """
        self.config = config or Config()
        self.extraction_service = ExtractionService(config=self.config)
        self.text_chunker = TextChunker()
        self.openai_pool: Optional[OpenAIClientPool] = None
        
        logger.info("ExtractionStage initialized")
    
    async def initialize(self, openai_pool: OpenAIClientPool) -> None:
        """
        Initialize with OpenAI pool.
        
        Args:
            openai_pool: Initialized OpenAI client pool
        """
        self.openai_pool = openai_pool
        logger.info("ExtractionStage connected to OpenAI pool")
    
    async def process_document(
        self,
        document: Document,
        progress_callback: Optional[callable] = None
    ) -> ExtractionResult:
        """
        Process single document through extraction pipeline.
        
        Args:
            document: Haystack document with markdown content
            progress_callback: Optional callback for progress updates
            
        Returns:
            ExtractionResult with all extracted data
        """
        file_id = document.meta.get("file_id", "")
        filename = document.meta.get("original_filename", "unknown")
        
        try:
            logger.info(f"Starting extraction for {filename}")
            
            # Step 1: Text chunking (no API call, fast)
            if progress_callback:
                await progress_callback("chunking", filename)
            
            chunks = await self._chunk_document(document)
            logger.debug(f"Created {len(chunks)} chunks for {filename}")
            
            # Step 2: Summary extraction (1st API call - RATE LIMITED)
            if progress_callback:
                await progress_callback("summary_extraction", filename)
            
            extraction = await self._extract_summary(document)
            if not extraction:
                return ExtractionResult(
                    file_id=file_id,
                    original_filename=filename,
                    error="Summary extraction failed",
                    success=False
                )
            
            logger.info(f"✓ Summary extracted for {filename}")
            
            # Step 3: Template extraction (2nd API call - RATE LIMITED)
            if progress_callback:
                await progress_callback("template_extraction", filename)
            
            template_facts = await self._extract_template_facts(extraction)
            logger.info(f"✓ Template facts extracted for {filename}")
            
            # Step 4: Create sections from extraction (includes template facts)
            sections = await self._create_sections(document, extraction, template_facts)
            logger.debug(f"Created {len(sections)} sections for {filename}")
            
            # Update document metadata
            document.meta["extraction"] = extraction
            document.meta["most_appropriate_section"] = extraction.metadata.most_appropriate_section
            
            return ExtractionResult(
                file_id=file_id,
                original_filename=filename,
                document=document,
                chunks=chunks,
                extraction=extraction.to_dict() if hasattr(extraction, 'to_dict') else extraction,
                sections=sections,
                template_facts=template_facts,
                success=True
            )
            
        except Exception as e:
            logger.error(f"Extraction failed for {filename}: {e}", exc_info=True)
            return ExtractionResult(
                file_id=file_id,
                original_filename=filename,
                error=str(e),
                success=False
            )
    
    async def _chunk_document(self, document: Document) -> List[Dict]:
        """Create text chunks (non-blocking)."""
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            self.text_chunker.run,
            [document]
        )
        
        chunks = result.get("chunks", [])
        return chunks
    
    async def _extract_summary(self, document: Document):
        """Extract summary using rate-limited API."""
        if not self.openai_pool:
            raise RuntimeError("OpenAI pool not initialized")
        
        # This will automatically rate-limit via OpenAI pool
        loop = asyncio.get_event_loop()
        extraction = await loop.run_in_executor(
            None,
            self.extraction_service.summary_extraction,
            document.content
        )
        
        return extraction
    
    async def _extract_template_facts(self, extraction) -> Optional[Dict]:
        """Extract template-specific facts using rate-limited API."""
        if not self.openai_pool:
            raise RuntimeError("OpenAI pool not initialized")
        
        # This will automatically rate-limit via OpenAI pool
        loop = asyncio.get_event_loop()
        template_facts = await loop.run_in_executor(
            None,
            self.extraction_service.template_fact_extraction,
            extraction
        )
        
        return template_facts
    
    async def _create_sections(
        self, 
        document: Document, 
        extraction,
        template_facts: Optional[Dict] = None
    ) -> List[Dict]:
        """Create sections from extraction including template facts."""
        file_id = document.meta.get("file_id", "")
        
        sections = []
        section_names = [
            "case_facts",
            "issues_for_determination",
            "evidence",
            "arguments",
            "reasoning",
            "judgement"
        ]
        
        for idx, section_name in enumerate(section_names):
            section_data = getattr(extraction, section_name, None)
            
            if section_data:
                # Convert to text
                if isinstance(section_data, list):
                    text = "\n".join(str(item) for item in section_data)
                elif hasattr(section_data, 'to_dict'):
                    text = json.dumps(section_data.to_dict(), indent=2)
                else:
                    text = str(section_data)
                
                sections.append({
                    "file_id": file_id,
                    "section_name": section_name,
                    "sequence_number": idx,
                    "text": text
                })
        
        # Add template_facts section if available
        if template_facts:
            template_section = self._create_template_facts_section(template_facts, file_id)
            sections.append(template_section)
            logger.debug(f"Added template_facts section: {template_facts.get('template_id', 'unknown')}")
        
        return sections
    
    def _create_template_facts_section(self, template_facts: Dict[str, Any], file_id: str) -> Dict[str, Any]:
        """Create a section dictionary from template-specific facts."""
        template_id = template_facts.get('template_id', 'Unknown')
        extracted_facts = template_facts.get('extracted_facts', {})
        
        # Format the template facts as readable text
        facts_text = f"Template: {template_id}\n\n"
        
        # Convert extracted facts to formatted text
        for key, value in extracted_facts.items():
            if isinstance(value, dict):
                facts_text += f"{key.upper()}:\n"
                for sub_key, sub_value in value.items():
                    if isinstance(sub_value, list):
                        facts_text += f"  {sub_key}: {', '.join(str(v) for v in sub_value)}\n"
                    else:
                        facts_text += f"  {sub_key}: {sub_value}\n"
                facts_text += "\n"
            elif isinstance(value, list):
                facts_text += f"{key}: {', '.join(str(v) for v in value)}\n"
            else:
                facts_text += f"{key}: {value}\n"
        
        return {
            "section_name": "template_Fact_extraction",
            "sequence_number": 6,
            "text": facts_text,
            "file_id": file_id
        }
    
    async def process_batch(
        self,
        documents: List[Document],
        progress_callback: Optional[callable] = None
    ) -> List[ExtractionResult]:
        """
        Process batch of documents sequentially (due to rate limiting).
        
        Args:
            documents: List of documents to process
            progress_callback: Optional callback for progress updates
            
        Returns:
            List of ExtractionResults
        """
        logger.info(f"Processing {len(documents)} documents (rate-limited extraction)...")
        
        results = []
        
        for doc in documents:
            result = await self.process_document(doc, progress_callback)
            results.append(result)
            
            # Small delay to ensure rate limiting
            await asyncio.sleep(0.1)
        
        success_count = sum(1 for r in results if r.success)
        failure_count = len(results) - success_count
        
        logger.info(f"Extraction complete: {success_count} success, {failure_count} failed")
        
        return results
