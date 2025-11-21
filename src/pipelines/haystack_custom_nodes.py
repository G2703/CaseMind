"""
Custom Haystack components for the ingestion pipeline.
Uses @component decorator following Haystack 2.0 patterns.
"""

import logging
import hashlib
import json
import openai
from pathlib import Path
from typing import List, Dict, Any, Optional
from haystack import component, Document
from haystack_integrations.document_stores.pgvector import PgvectorDocumentStore

logger = logging.getLogger(__name__)


@component
class DuplicateCheckNode:
    """
    Haystack component that checks if document already exists in database.
    Uses file hash for duplicate detection.
    """
    
    def __init__(self, document_store: PgvectorDocumentStore):
        """
        Initialize duplicate checker.
        
        Args:
            document_store: PgvectorDocumentStore instance
        """
        self.document_store = document_store
        logger.info("DuplicateCheckNode initialized")
    
    @component.output_types(documents=List[Document], is_duplicate=bool)
    def run(self, documents: List[Document]) -> dict:
        """
        Check if documents exist in database by file hash.
        
        Args:
            documents: List of Haystack Documents
            
        Returns:
            dict with documents and is_duplicate flag
        """
        if not documents:
            return {"documents": [], "is_duplicate": False}
        
        # Check first document (single file ingestion)
        doc = documents[0]
        file_hash = doc.meta.get("file_hash")
        
        if not file_hash:
            logger.warning("No file_hash in document metadata, cannot check for duplicates")
            return {"documents": documents, "is_duplicate": False}
        
        # Query document store for existing hash
        try:
            existing_docs = self.document_store.filter_documents(
                filters={"field": "meta.file_hash", "operator": "==", "value": file_hash}
            )
            
            if existing_docs:
                logger.info(f"Duplicate found: {existing_docs[0].id}")
                return {"documents": documents, "is_duplicate": True}
            else:
                logger.info("No duplicate found")
                return {"documents": documents, "is_duplicate": False}
                
        except Exception as e:
            logger.error(f"Error checking for duplicates: {e}")
            return {"documents": documents, "is_duplicate": False}


@component
class TemplateLoaderNode:
    """
    Haystack component that loads appropriate template based on metadata.
    Selects template from most_appropriate_section field.
    """
    
    def __init__(self, templates_dir: str):
        """
        Initialize template loader.
        
        Args:
            templates_dir: Path to templates directory
        """
        self.templates_dir = Path(templates_dir)
        self.templates = self._load_all_templates()
        logger.info(f"TemplateLoaderNode initialized with {len(self.templates)} templates")
    
    def _load_all_templates(self) -> Dict[str, dict]:
        """Load all template JSON files."""
        templates = {}
        
        if not self.templates_dir.exists():
            logger.warning(f"Templates directory not found: {self.templates_dir}")
            return templates
        
        for template_file in self.templates_dir.glob("*.json"):
            if template_file.name == "templates.json":
                continue
            
            try:
                with open(template_file, 'r', encoding='utf-8') as f:
                    template_data = json.load(f)
                
                template_id = template_file.stem
                templates[template_id] = template_data
                
            except Exception as e:
                logger.warning(f"Failed to load template {template_file}: {e}")
        
        return templates
    
    def _match_section_to_template(self, section: str) -> str:
        """Match legal section to template ID."""
        section_normalized = section.lower().replace(' ', '_')
        
        # Direct mapping for IPC sections
        ipc_mappings = {
            'ipc_302': 'ipc_302',
            'ipc_304': 'ipc_304_p2',
            'ipc_306': 'ipc_306',
            'ipc_307': 'ipc_307',
            'ipc_323': 'ipc_323',
            'ipc_324': 'ipc_324',
            'ipc_354': 'ipc_354',
            'ipc_354a': 'ipc_354a',
            'ipc_363': 'ipc_363',
            'ipc_376': 'ipc_376',
            'ipc_379': 'ipc_379',
            'ipc_380': 'ipc_380',
            'ipc_392': 'ipc_392',
            'ipc_394': 'ipc_394',
            'ipc_395': 'ipc_395',
            'ipc_397': 'ipc_397',
            'ipc_498a': 'ipc_498a',
        }
        
        # Check direct mappings
        for pattern, template_id in ipc_mappings.items():
            if pattern in section_normalized:
                if template_id in self.templates:
                    return template_id
        
        # Fallback to generic template
        return 'legal_case'
    
    @component.output_types(documents=List[Document], template=dict)
    def run(self, documents: List[Document]) -> dict:
        """
        Load template based on document metadata.
        
        Args:
            documents: List of Haystack Documents with metadata
            
        Returns:
            dict with documents and selected template
        """
        if not documents:
            return {"documents": [], "template": {}}
        
        doc = documents[0]
        most_appropriate_section = doc.meta.get("most_appropriate_section", "Unknown")
        
        # Match section to template
        template_id = self._match_section_to_template(most_appropriate_section)
        template_data = self.templates.get(template_id, self.templates.get('legal_case', {}))
        
        logger.info(f"Selected template: {template_id} for section: {most_appropriate_section}")
        
        # Add template info to document metadata
        doc.meta["template_id"] = template_id
        doc.meta["template_label"] = template_data.get("label", template_id)
        
        return {"documents": documents, "template": template_data}


@component
class FactExtractorNode:
    """
    Haystack component for extracting facts using OpenAI structured output.
    Extracts facts based on template schema.
    """
    
    def __init__(self, api_key: str, model: str = "gpt-4o-2024-08-06"):
        """
        Initialize fact extractor.
        
        Args:
            api_key: OpenAI API key
            model: OpenAI model to use
        """
        self.api_key = api_key
        self.model = model
        self.client = openai.OpenAI(api_key=api_key)
        logger.info(f"FactExtractorNode initialized with model: {model}")
    
    def _create_fact_extraction_prompt(self, text: str, template: dict) -> str:
        """Create prompt for fact extraction."""
        template_label = template.get("label", "Legal Case")
        schema = template.get("json_schema", {}).get("schema", {})
        schema_str = json.dumps(schema, indent=2)
        
        prompt = f"""You are a legal document analyzer. Extract structured facts from the given legal case text according to the provided template schema.

        Template: {template_label}
        Template Schema:
        {schema_str}

        Guidelines:
        - Extract facts according to the schema structure
        - Return ONLY valid JSON matching the schema
        - Use null for missing information
        - Be precise and factual

        Legal Case Text:
        {text}

        Return the extracted facts as a JSON object matching the schema exactly."""
                
        return prompt
    
    @component.output_types(documents=List[Document], success=bool)
    def run(self, documents: List[Document], template: dict) -> dict:
        """
        Extract facts from documents using template schema.
        
        Args:
            documents: List of Haystack Documents
            template: Template dictionary with schema
            
        Returns:
            dict with documents enriched with extracted facts and success flag
        """
        if not documents or not template:
            return {"documents": documents, "success": False}
        
        doc = documents[0]
        text = doc.content
        
        # Truncate text if too long
        max_chars = 6000
        if len(text) > max_chars:
            logger.warning(f"Text truncated from {len(text)} to {max_chars} characters")
            text = text[:max_chars] + "\n... [truncated]"
        
        try:
            # Build prompt
            prompt = self._create_fact_extraction_prompt(text, template)
            
            logger.info("Calling OpenAI API for fact extraction...")
            
            # Call OpenAI API with structured output
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a legal document fact extractor. Always return valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.5,
                max_tokens=2000,
                response_format={"type": "json_object"}
            )
            
            # Parse response
            response_text = response.choices[0].message.content.strip()
            facts = json.loads(response_text)
            
            # Generate facts summary
            facts_summary = self._generate_facts_summary(facts)
            
            # Add to document metadata
            doc.meta["extracted_facts"] = facts
            doc.meta["facts_summary"] = facts_summary
            
            # Update document content to facts summary for embedding
            doc.content = facts_summary
            
            logger.info("Facts extracted successfully")
            return {"documents": [doc], "success": True}
            
        except Exception as e:
            logger.error(f"Failed to extract facts: {e}")
            # Don't pass document forward if extraction failed
            doc.meta["extracted_facts"] = {}
            doc.meta["facts_summary"] = ""
            doc.meta["extraction_error"] = str(e)
            return {"documents": [], "success": False}
    
    def _generate_facts_summary(self, facts: dict) -> str:
        """Generate human-readable summary from extracted facts."""
        summary_parts = []
        
        for tier_name, tier_data in facts.items():
            if isinstance(tier_data, dict):
                for key, value in tier_data.items():
                    if value and value != "null":
                        summary_parts.append(f"{key}: {value}")
        
        return "\n".join(summary_parts) if summary_parts else "No facts extracted"


@component
class ThresholdFilterNode:
    """
    Haystack component that filters documents based on score threshold.
    Used after reranking to keep only high-quality results.
    """
    
    def __init__(self, threshold: float = 0.0):
        """
        Initialize threshold filter.
        
        Args:
            threshold: Minimum score threshold (documents below this are filtered out)
        """
        self.threshold = threshold
        logger.info(f"ThresholdFilterNode initialized with threshold: {threshold}")
    
    @component.output_types(documents=List[Document])
    def run(self, documents: List[Document]) -> dict:
        """
        Filter documents by score threshold.
        
        Args:
            documents: List of Haystack Documents with scores
            
        Returns:
            dict with filtered documents
        """
        if not documents:
            return {"documents": []}
        
        # Filter documents with score >= threshold
        filtered = []
        for doc in documents:
            score = doc.score if hasattr(doc, 'score') else 0.0
            if score >= self.threshold:
                filtered.append(doc)
        
        logger.info(f"Filtered {len(documents)} documents to {len(filtered)} above threshold {self.threshold}")
        return {"documents": filtered}

