"""
Custom Haystack components for the ingestion pipeline.
Uses @component decorator following Haystack 2.0 patterns.
"""

import logging
import hashlib
import json
import openai
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
from haystack import component, Document
from haystack_integrations.document_stores.pgvector import PgvectorDocumentStore

logger = logging.getLogger(__name__)


@component
class MarkdownSaverNode:
    """
    Haystack component that saves markdown content to disk.
    Saves to cases/markdown folder.
    """
    
    def __init__(self, output_dir: str = "cases/markdown"):
        """
        Initialize markdown saver.
        
        Args:
            output_dir: Directory to save markdown files
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"MarkdownSaverNode initialized with output_dir: {output_dir}")
    
    @component.output_types(documents=List[Document])
    def run(self, documents: List[Document]) -> dict:
        """
        Save markdown content to disk.
        
        Args:
            documents: List of Haystack Documents with markdown content
            
        Returns:
            dict with documents (unchanged)
        """
        if not documents:
            return {"documents": []}
        
        doc = documents[0]
        
        try:
            # Get filename from metadata
            original_filename = doc.meta.get("original_filename", "unknown.pdf")
            base_name = Path(original_filename).stem
            output_file = self.output_dir / f"{base_name}.md"
            
            # Save markdown content
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(doc.content)
            
            logger.info(f"Saved markdown to: {output_file}")
            
        except Exception as e:
            logger.error(f"Failed to save markdown: {e}")
        
        return {"documents": documents}


@component
class TemplateSaverNode:
    """
    Haystack component that saves filled template to disk.
    Saves to cases/extracted folder.
    """
    
    def __init__(self, output_dir: str = "cases/extracted"):
        """
        Initialize template saver.
        
        Args:
            output_dir: Directory to save filled templates
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"TemplateSaverNode initialized with output_dir: {output_dir}")
    
    @component.output_types(documents=List[Document])
    def run(self, documents: List[Document]) -> dict:
        """
        Save filled template to disk.
        
        Args:
            documents: List of Haystack Documents with extracted facts
            
        Returns:
            dict with documents (unchanged)
        """
        if not documents:
            return {"documents": []}
        
        doc = documents[0]
        
        try:
            # Get extracted facts from metadata
            extracted_facts = doc.meta.get("extracted_facts", {})

            if not extracted_facts:
                logger.warning("No extracted facts to save")
                return {"documents": documents}

            # Ensure template metadata fields are present in the saved template
            # Use values from document metadata when available, with sensible fallbacks
            extracted_facts["template_id"] = doc.meta.get("template_id", "")
            extracted_facts["template_label"] = doc.meta.get("template_label", extracted_facts.get("template_label", ""))
            # extraction_confidence may come from multiple keys; fall back to 0.0 if missing
            extracted_facts["extraction_confidence"] = doc.meta.get(
                "extraction_confidence",
                doc.meta.get("confidence_score", extracted_facts.get("extraction_confidence", 0.0))
            )
            # extraction_timestamp: prefer explicit meta value, otherwise use current UTC timestamp
            extracted_facts["extraction_timestamp"] = doc.meta.get(
                "extraction_timestamp",
                datetime.utcnow().isoformat() + "Z"
            )

            # Get filename from metadata
            original_filename = doc.meta.get("original_filename", "unknown.pdf")
            base_name = Path(original_filename).stem
            output_file = self.output_dir / f"{base_name}_facts.json"

            # Save filled template as JSON
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(extracted_facts, f, indent=2, ensure_ascii=False)

            logger.info(f"Saved filled template to: {output_file}")
            
        except Exception as e:
            logger.error(f"Failed to save template: {e}")
        
        return {"documents": documents}


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
        
        # Query document store for existing hash using direct SQL
        try:
            import psycopg2
            
            conn_str = str(self.document_store.connection_string.resolve_value())
            conn = psycopg2.connect(conn_str)
            cursor = conn.cursor()
            
            # Check if document with this file_hash already exists
            cursor.execute("""
                SELECT id FROM haystack_documents 
                WHERE meta->>'file_hash' = %s
                LIMIT 1
            """, (file_hash,))
            
            existing = cursor.fetchone()
            cursor.close()
            conn.close()
            
            if existing:
                logger.info(f"Duplicate found with file_hash: {file_hash}")
                # Return empty documents list to stop pipeline execution
                return {"documents": [], "is_duplicate": True}
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

        **EXTRACTION GUIDELINES**:

        **TIER 1 - DETERMINATIVE FACTS**: Core facts that determine guilt, liability, or legal outcomes
        **TIER 2 - MATERIAL FACTS**: Facts that significantly affect rights, duties, or case outcome  
        **TIER 3 - CONTEXTUAL FACTS**: Environmental and circumstantial details
        **TIER 4 - PROCEDURAL FACTS**: Court metadata, case details, and procedural information
        **RESIDUAL DETAILS**: Any other relevant facts not captured above

        **CRITICAL EXTRACTION RULES**:
        1. Write each extracted value as a complete, coherent sentence that makes sense on its own
        2. When concatenated together, all extracted facts should form a readable narrative summary
        3. Each fact should flow naturally into the next when combined
        4. Use transitional phrases and connecting words to ensure readability
        5. Extract facts directly from the case text with narrative coherence
        6. Be comprehensive and accurate while maintaining story flow
        7. If a field is not found in the text, use null
        8. Organize facts according to their legal significance
        9. Each extracted fact should contribute to a unified case story when all values are joined together

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
            
            # DO NOT replace doc.content - DualEmbedderNode will handle it
            # Keep original content intact for now
            
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
        """Generate human-readable summary from extracted facts by concatenating all non-null values."""
        summary_parts = []
        
        def extract_values(obj):
            """Recursively extract all non-null values from nested structure."""
            if isinstance(obj, dict):
                for value in obj.values():
                    extract_values(value)
            elif isinstance(obj, list):
                for item in obj:
                    extract_values(item)
            elif obj is not None and str(obj).strip() and str(obj).lower() != "null":
                summary_parts.append(str(obj))
        
        extract_values(facts)
        return " ".join(summary_parts) if summary_parts else "No facts extracted"


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


@component
class DualEmbedderNode:
    """
    Haystack component that creates two embeddings per document:
    1. Facts embedding (from extracted facts template)
    2. Metadata embedding (from concatenated metadata fields)
    
    Also handles storing both embeddings to PostgreSQL.
    """
    
    def __init__(self, document_store: PgvectorDocumentStore, model: str = "sentence-transformers/all-mpnet-base-v2"):
        """
        Initialize dual embedder.
        
        Args:
            document_store: PgvectorDocumentStore instance
            model: Sentence transformer model name
        """
        from sentence_transformers import SentenceTransformer
        
        self.document_store = document_store
        self.model_name = model
        self.model = SentenceTransformer(model)
        logger.info(f"DualEmbedderNode initialized with model: {model}")
    
    def _format_template_as_text(self, facts: dict) -> str:
        """
        Format the entire extracted facts template as text for embedding.
        Includes all fields and values from the filled template.
        """
        parts = []
        
        def extract_all_text(obj, prefix=""):
            """Recursively extract all text from nested structure."""
            if isinstance(obj, dict):
                for key, value in obj.items():
                    new_prefix = f"{prefix}.{key}" if prefix else key
                    extract_all_text(value, new_prefix)
            elif isinstance(obj, list):
                for i, item in enumerate(obj):
                    extract_all_text(item, f"{prefix}[{i}]")
            elif obj is not None and str(obj).strip():
                parts.append(f"{prefix}: {obj}")
        
        extract_all_text(facts)
        return " | ".join(parts) if parts else ""
    
    def _format_metadata_as_text(self, meta: dict) -> str:
        """
        Format metadata fields as concatenated text for embedding.
        """
        metadata_fields = []
        
        # Extract key metadata fields
        if meta.get('case_title'):
            metadata_fields.append(meta['case_title'])
        if meta.get('court_name'):
            metadata_fields.append(meta['court_name'])
        if meta.get('judgment_date'):
            metadata_fields.append(meta['judgment_date'])
        if meta.get('sections_invoked'):
            sections = meta['sections_invoked']
            if isinstance(sections, list):
                metadata_fields.extend(sections)
            else:
                metadata_fields.append(str(sections))
        if meta.get('most_appropriate_section'):
            metadata_fields.append(meta['most_appropriate_section'])
        
        return " ".join(metadata_fields)
    
    @component.output_types(documents=List[Document])
    def run(self, documents: List[Document]) -> dict:
        """
        Create dual embeddings and store to database.
        
        Args:
            documents: List of Haystack Documents with extracted facts
            
        Returns:
            dict with documents (embeddings stored in DB)
        """
        if not documents:
            return {"documents": []}
        
        doc = documents[0]
        
        try:
            # Extract facts and metadata
            extracted_facts = doc.meta.get("extracted_facts", {})
            facts_summary = doc.meta.get("facts_summary", "")
            
            # 1. Create facts embedding (from full template)
            facts_text = self._format_template_as_text(extracted_facts)
            if not facts_text:
                logger.warning("No facts text to embed, using content")
                facts_text = doc.content
            
            facts_embedding = self.model.encode(facts_text, convert_to_numpy=True)
            logger.info(f"Created facts embedding from full template (dim: {len(facts_embedding)})")
            
            # 2. Create metadata embedding
            metadata_text = self._format_metadata_as_text(doc.meta)
            metadata_embedding = self.model.encode(metadata_text, convert_to_numpy=True)
            logger.info(f"Created metadata embedding (dim: {len(metadata_embedding)})")
            
            # 3. Update doc.content to facts_summary for display/retrieval purposes
            if facts_summary and len(facts_summary.strip()) > 0:
                doc.content = facts_summary
                logger.info(f"Set doc.content to facts_summary ({len(facts_summary)} chars)")
            elif facts_text:
                # Fallback: use formatted facts text if summary is empty
                doc.content = facts_text[:1000]  # Limit to reasonable length
                logger.warning(f"Facts summary empty, using formatted facts text ({len(doc.content)} chars)")
            else:
                doc.content = "No facts extracted"
                logger.warning("Both facts_summary and facts_text are empty")
            
            # 4. Store both embeddings to PostgreSQL
            # Haystack's writer only handles the 'embedding' column, so we need custom SQL
            import psycopg2
            from psycopg2.extras import Json
            import numpy as np
            
            conn_str = str(self.document_store.connection_string.resolve_value())
            conn = psycopg2.connect(conn_str)
            cursor = conn.cursor()
            
            # Prepare document data
            doc_id = doc.id
            content = doc.content
            meta_json = Json(doc.meta)
            
            # Insert/Update with both embeddings
            cursor.execute("""
                INSERT INTO haystack_documents (id, content, meta, embedding, embedding_metadata)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE
                SET content = EXCLUDED.content,
                    meta = EXCLUDED.meta,
                    embedding = EXCLUDED.embedding,
                    embedding_metadata = EXCLUDED.embedding_metadata;
            """, (doc_id, content, meta_json, facts_embedding.tolist(), metadata_embedding.tolist()))
            
            conn.commit()
            cursor.close()
            conn.close()
            
            logger.info(f"Successfully stored document with dual embeddings: {doc_id}")
            
            return {"documents": [doc]}
            
        except Exception as e:
            logger.error(f"Failed to create dual embeddings: {e}")
            return {"documents": []}


@component
class FactsEmbeddingRetriever:
    """
    Custom retriever that searches using the 'embedding' column (facts embedding).
    This is the default search mode - searching based on case facts.
    """
    
    def __init__(self, document_store: PgvectorDocumentStore, top_k: int = 10):
        """
        Initialize facts embedding retriever.
        
        Args:
            document_store: PgvectorDocumentStore instance
            top_k: Number of documents to retrieve
        """
        self.document_store = document_store
        self.top_k = top_k
        logger.info(f"FactsEmbeddingRetriever initialized with top_k={top_k}")
    
    @component.output_types(documents=List[Document])
    def run(self, query_embedding: List[float], filters: Optional[Dict[str, Any]] = None) -> dict:
        """
        Retrieve documents using facts embedding (standard embedding column).
        
        Args:
            query_embedding: Query embedding vector
            filters: Optional filters for document retrieval
            
        Returns:
            dict with retrieved documents
        """
        try:
            import psycopg2
            from psycopg2.extras import RealDictCursor
            
            conn_str = str(self.document_store.connection_string.resolve_value())
            conn = psycopg2.connect(conn_str)
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            # Query using facts embedding (standard 'embedding' column)
            # Note: We search on 'embedding' which contains facts embedding
            query_vector = query_embedding
            
            # Build SQL query
            sql = """
                SELECT id, content, meta, 
                       1 - (embedding <=> %s::vector) AS score
                FROM haystack_documents
                WHERE embedding IS NOT NULL
            """
            
            params = [query_vector]
            
            # Add filters if provided (simplified - you may need more complex filter handling)
            if filters:
                # Handle basic 'id' filter
                if 'field' in filters and filters['field'] == 'id':
                    operator = filters.get('operator', '!=')
                    value = filters.get('value')
                    if operator == '!=':
                        sql += " AND id != %s"
                        params.append(value)
            
            sql += f" ORDER BY score DESC LIMIT {self.top_k}"
            
            cursor.execute(sql, params)
            rows = cursor.fetchall()
            
            # Convert to Haystack Documents
            documents = []
            for row in rows:
                doc = Document(
                    id=row['id'],
                    content=row['content'],
                    meta=row['meta'] or {},
                    score=float(row['score'])
                )
                # Store cosine similarity in meta for later use
                doc.meta['score'] = float(row['score'])
                documents.append(doc)
            
            cursor.close()
            conn.close()
            
            logger.info(f"Retrieved {len(documents)} documents using facts embedding")
            return {"documents": documents}
            
        except Exception as e:
            logger.error(f"Facts embedding retrieval failed: {e}")
            return {"documents": []}

