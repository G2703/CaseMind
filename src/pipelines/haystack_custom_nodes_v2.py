"""
New custom Haystack components for the optimized ingestion pipeline.
Implements comprehensive case summarization with multi-field embedding strategy.
"""

import logging
import json
import openai
import psycopg2
from psycopg2.extras import Json, RealDictCursor
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
from haystack import component, Document
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)


@component
class SummaryPostProcessorNode:
    """
    Post-processes LLM output from case summarization.
    Validates nested JSON structure and ensures all required sections exist.
    """
    
    def __init__(self):
        """Initialize summary post-processor."""
        logger.info("SummaryPostProcessorNode initialized")
    
    def _validate_summary_structure(self, summary: dict) -> dict:
        """
        Validate and fill missing sections in summary JSON.
        
        Args:
            summary: Extracted summary JSON
            
        Returns:
            Validated summary with all required sections
        """
        # Ensure all main sections exist
        required_sections = [
            "metadata", "case_facts", "issues_for_determination",
            "evidence", "arguments", "reasoning", "judgement"
        ]
        
        for section in required_sections:
            if section not in summary:
                summary[section] = {}
        
        # Validate metadata subsections
        if "metadata" in summary and isinstance(summary["metadata"], dict):
            if "lower_court_history" not in summary["metadata"]:
                summary["metadata"]["lower_court_history"] = {
                    "trial_court_verdict": "",
                    "high_court_verdict": ""
                }
        
        return summary
    
    @component.output_types(documents=List[Document])
    def run(self, documents: List[Document]) -> dict:
        """
        Post-process and validate summarization output.
        
        Args:
            documents: List of Haystack Documents with extracted summary in meta
            
        Returns:
            dict with validated documents
        """
        if not documents:
            return {"documents": []}
        
        doc = documents[0]
        
        try:
            # Get summary from metadata (LLMMetadataExtractor puts it there)
            # Extract from meta keys
            metadata = doc.meta.get("metadata", {})
            case_facts = doc.meta.get("case_facts", {})
            issues = doc.meta.get("issues_for_determination", [])
            evidence = doc.meta.get("evidence", {})
            arguments = doc.meta.get("arguments", {})
            reasoning = doc.meta.get("reasoning", {})
            judgement = doc.meta.get("judgement", {})
            
            # Build complete summary structure
            summary = {
                "metadata": metadata,
                "case_facts": case_facts,
                "issues_for_determination": issues,
                "evidence": evidence,
                "arguments": arguments,
                "reasoning": reasoning,
                "judgement": judgement
            }
            
            # Validate structure
            summary = self._validate_summary_structure(summary)
            
            # Store complete summary in meta
            doc.meta["summary"] = summary
            
            logger.info("Summary post-processing completed successfully")
            return {"documents": [doc]}
            
        except Exception as e:
            logger.error(f"Failed to post-process summary: {e}")
            # Return document with empty summary on error
            doc.meta["summary"] = {
                "metadata": {}, "case_facts": {}, "issues_for_determination": [],
                "evidence": {}, "arguments": {}, "reasoning": {}, "judgement": {}
            }
            return {"documents": [doc]}


@component
class MultiSectionEmbedderNode:
    """
    Creates 7 separate embeddings from the case summary:
    1. metadata_embedding
    2. case_facts_embedding
    3. issues_embedding
    4. evidence_embedding
    5. arguments_embedding
    6. reasoning_embedding
    7. judgement_embedding
    """
    
    def __init__(self, model: str = "sentence-transformers/all-mpnet-base-v2"):
        """
        Initialize multi-section embedder.
        
        Args:
            model: Sentence transformer model name
        """
        self.model_name = model
        self.model = SentenceTransformer(model)
        logger.info(f"MultiSectionEmbedderNode initialized with model: {model}")
    
    @component.output_types(documents=List[Document])
    def run(self, documents: List[Document]) -> dict:
        """
        Create embeddings for each section of the summary.
        
        Args:
            documents: List of Haystack Documents with summary in meta
            
        Returns:
            dict with documents enriched with section embeddings in meta
        """
        if not documents:
            return {"documents": []}
        
        doc = documents[0]
        
        try:
            summary = doc.meta.get("summary", {})
            
            # Create embeddings for each section using raw JSON strings
            embeddings = {}
            
            # 1. Metadata embedding
            metadata_json = json.dumps(summary.get("metadata", {}))
            embeddings["metadata_embedding"] = self.model.encode(metadata_json, convert_to_numpy=True).tolist()
            
            # 2. Case facts embedding
            case_facts_json = json.dumps(summary.get("case_facts", {}))
            embeddings["case_facts_embedding"] = self.model.encode(case_facts_json, convert_to_numpy=True).tolist()
            
            # 3. Issues embedding
            issues_json = json.dumps(summary.get("issues_for_determination", []))
            embeddings["issues_embedding"] = self.model.encode(issues_json, convert_to_numpy=True).tolist()
            
            # 4. Evidence embedding
            evidence_json = json.dumps(summary.get("evidence", {}))
            embeddings["evidence_embedding"] = self.model.encode(evidence_json, convert_to_numpy=True).tolist()
            
            # 5. Arguments embedding
            arguments_json = json.dumps(summary.get("arguments", {}))
            embeddings["arguments_embedding"] = self.model.encode(arguments_json, convert_to_numpy=True).tolist()
            
            # 6. Reasoning embedding
            reasoning_json = json.dumps(summary.get("reasoning", {}))
            embeddings["reasoning_embedding"] = self.model.encode(reasoning_json, convert_to_numpy=True).tolist()
            
            # 7. Judgement embedding
            judgement_json = json.dumps(summary.get("judgement", {}))
            embeddings["judgement_embedding"] = self.model.encode(judgement_json, convert_to_numpy=True).tolist()
            
            # Store all embeddings in document metadata
            doc.meta.update(embeddings)
            
            logger.info("Created 7 section embeddings successfully")
            return {"documents": [doc]}
            
        except Exception as e:
            logger.error(f"Failed to create section embeddings: {e}")
            return {"documents": []}


@component
class TemplateSelectorNode:
    """
    Selects appropriate template based on most_appropriate_section from metadata.
    Fallback to legal_case template if section not found or Unknown.
    """
    
    def __init__(self, templates_dir: str):
        """
        Initialize template selector.
        
        Args:
            templates_dir: Path to templates directory
        """
        self.templates_dir = Path(templates_dir)
        self.templates = self._load_all_templates()
        logger.info(f"TemplateSelectorNode initialized with {len(self.templates)} templates")
    
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
        if not section or section.lower() in ["unknown", "null", ""]:
            return "legal_case"
        
        section_normalized = section.lower().replace(' ', '_')
        
        # Direct template mappings
        section_mappings = {
            'ipc_302': 'ipc_302', 'ipc_304': 'ipc_304_p2', 'ipc_306': 'ipc_306',
            'ipc_307': 'ipc_307', 'ipc_316': 'ipc_316', 'ipc_320': 'ipc_320',
            'ipc_323': 'ipc_323', 'ipc_324': 'ipc_324', 'ipc_354': 'ipc_354',
            'ipc_354a': 'ipc_354a', 'ipc_363': 'ipc_363', 'ipc_376': 'ipc_376',
            'ipc_379': 'ipc_379', 'ipc_380': 'ipc_380', 'ipc_384': 'ipc_384',
            'ipc_392': 'ipc_392', 'ipc_394': 'ipc_394', 'ipc_395': 'ipc_395',
            'ipc_397': 'ipc_397', 'ipc_399': 'ipc_399', 'ipc_402': 'ipc_402',
            'ipc_427': 'ipc_427', 'ipc_452': 'ipc_452', 'ipc_457': 'ipc_457',
            'ipc_498a': 'ipc_498a'
        }
        
        # Check direct mappings
        for pattern, template_id in section_mappings.items():
            if pattern in section_normalized:
                if template_id in self.templates:
                    logger.info(f"Matched section '{section}' to template '{template_id}'")
                    return template_id
        
        # Fallback to generic template
        logger.info(f"No specific template for section '{section}', using 'legal_case'")
        return 'legal_case'
    
    @component.output_types(documents=List[Document], template=dict, template_id=str)
    def run(self, documents: List[Document]) -> dict:
        """
        Select template based on most_appropriate_section in summary metadata.
        
        Args:
            documents: List of Haystack Documents with summary
            
        Returns:
            dict with documents, selected template, and template_id
        """
        if not documents:
            return {"documents": [], "template": {}, "template_id": ""}
        
        doc = documents[0]
        
        try:
            summary = doc.meta.get("summary", {})
            metadata = summary.get("metadata", {})
            most_appropriate_section = metadata.get("most_appropriate_section", "Unknown")
            
            # Match section to template
            template_id = self._match_section_to_template(most_appropriate_section)
            template_data = self.templates.get(template_id, self.templates.get('legal_case', {}))
            
            # Add template info to document metadata
            doc.meta["template_id"] = template_id
            doc.meta["template_label"] = template_data.get("label", template_id)
            
            logger.info(f"Selected template: {template_id} for section: {most_appropriate_section}")
            
            return {"documents": [doc], "template": template_data, "template_id": template_id}
            
        except Exception as e:
            logger.error(f"Failed to select template: {e}")
            fallback_template = self.templates.get('legal_case', {})
            return {"documents": [doc], "template": fallback_template, "template_id": "legal_case"}


@component
class FactsExtractorNodeV2:
    """
    Extracts facts from case_facts + evidence sections ONLY (not full markdown).
    Optimized for token efficiency.
    """
    
    def __init__(self, api_key: str, model: str = "gpt-4o-2024-08-06"):
        """
        Initialize facts extractor.
        
        Args:
            api_key: OpenAI API key
            model: OpenAI model to use
        """
        self.api_key = api_key
        self.model = model
        self.client = openai.OpenAI(api_key=api_key)
        logger.info(f"FactsExtractorNodeV2 initialized with model: {model}")
    
    def _create_fact_extraction_prompt(self, case_facts_json: str, evidence_json: str, template: dict) -> str:
        """Create optimized prompt for fact extraction (Tiers 1-3 only, no Tier 4)."""
        template_label = template.get("label", "Legal Case")
        schema = template.get("json_schema", {}).get("schema", {})
        schema_str = json.dumps(schema, indent=2)
        
        prompt = f"""Extract structured facts from the case information below. Return ONLY valid JSON.

**Template**: {template_label}

**Case Facts**:
{case_facts_json}

**Evidence**:
{evidence_json}

**EXTRACTION TIERS**:
- **TIER 1 (Determinative)**: Core facts determining guilt/liability/outcomes
- **TIER 2 (Material)**: Facts significantly affecting rights/duties/outcomes  
- **TIER 3 (Contextual)**: Environmental and circumstantial details
- **RESIDUAL**: Other relevant facts

**RULES**:
1. Extract ONLY from case_facts and evidence above
2. Write complete, coherent sentences that form a readable narrative
3. Use null for missing fields
4. Stay within provided information - no inference

**Schema**:
{schema_str}

Return JSON matching the schema exactly."""
                
        return prompt
    
    @component.output_types(documents=List[Document], success=bool)
    def run(self, documents: List[Document], template: dict) -> dict:
        """
        Extract facts using only case_facts and evidence sections from summary.
        
        Args:
            documents: List of Haystack Documents with summary
            template: Template dictionary with schema
            
        Returns:
            dict with documents enriched with extracted facts and success flag
        """
        if not documents or not template:
            return {"documents": [], "success": False}
        
        doc = documents[0]
        
        try:
            summary = doc.meta.get("summary", {})
            case_facts = summary.get("case_facts", {})
            evidence = summary.get("evidence", {})
            
            # Convert to JSON strings for prompt
            case_facts_json = json.dumps(case_facts, indent=2)
            evidence_json = json.dumps(evidence, indent=2)
            
            # Build prompt
            prompt = self._create_fact_extraction_prompt(case_facts_json, evidence_json, template)
            
            logger.info("Calling OpenAI API for fact extraction (optimized input)...")
            
            # Call OpenAI API with structured output
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a legal document fact extractor. Always return valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.5,
                max_tokens=4096,  # Increased for template filling
                response_format={"type": "json_object"}
            )
            
            # Parse response
            response_text = response.choices[0].message.content.strip()
            facts = json.loads(response_text)
            
            # Add extraction metadata
            facts["extraction_timestamp"] = datetime.utcnow().isoformat() + "Z"
            
            # Store filled template
            doc.meta["factual_summary"] = facts
            
            logger.info("Facts extracted successfully (optimized)")
            return {"documents": [doc], "success": True}
            
        except Exception as e:
            logger.error(f"Failed to extract facts: {e}")
            doc.meta["factual_summary"] = {}
            doc.meta["extraction_error"] = str(e)
            return {"documents": [], "success": False}


@component
class FactsEmbedderNode:
    """
    Creates embedding from the filled template (factual_summary).
    This is the PRIMARY embedding used for similarity search.
    """
    
    def __init__(self, model: str = "sentence-transformers/all-mpnet-base-v2"):
        """
        Initialize facts embedder.
        
        Args:
            model: Sentence transformer model name
        """
        self.model_name = model
        self.model = SentenceTransformer(model)
        logger.info(f"FactsEmbedderNode initialized with model: {model}")
    
    @component.output_types(documents=List[Document])
    def run(self, documents: List[Document]) -> dict:
        """
        Create embedding from factual_summary (filled template).
        
        Args:
            documents: List of Haystack Documents with factual_summary
            
        Returns:
            dict with documents enriched with facts_embedding
        """
        if not documents:
            return {"documents": []}
        
        doc = documents[0]
        
        try:
            factual_summary = doc.meta.get("factual_summary", {})
            
            # Convert to JSON string for embedding
            facts_json = json.dumps(factual_summary)
            
            # Create embedding
            facts_embedding = self.model.encode(facts_json, convert_to_numpy=True).tolist()
            
            # Store in metadata
            doc.meta["facts_embedding"] = facts_embedding
            
            logger.info(f"Created facts embedding from filled template (dim: {len(facts_embedding)})")
            return {"documents": [doc]}
            
        except Exception as e:
            logger.error(f"Failed to create facts embedding: {e}")
            return {"documents": []}


@component
class LegalCaseDBWriterNode:
    """
    Writes complete case data to legal_cases table.
    Stores summary (JSONB), 7 section embeddings, factual_summary (JSONB), and facts_embedding.
    """
    
    def __init__(self, db_config: Dict[str, str]):
        """
        Initialize legal case DB writer.
        
        Args:
            db_config: Database configuration dict with host, port, user, password, database
        """
        self.db_config = db_config
        self.conn_str = f"postgresql://{db_config['user']}:{db_config['password']}@{db_config['host']}:{db_config['port']}/{db_config['database']}"
        logger.info("LegalCaseDBWriterNode initialized")
    
    @component.output_types(documents=List[Document], success=bool)
    def run(self, documents: List[Document]) -> dict:
        """
        Write case data to legal_cases table.
        
        Args:
            documents: List of Haystack Documents with all processed data
            
        Returns:
            dict with documents and success flag
        """
        if not documents:
            return {"documents": [], "success": False}
        
        doc = documents[0]
        
        try:
            # Extract all required data
            file_id = doc.id
            summary = doc.meta.get("summary", {})
            metadata = summary.get("metadata", {})
            
            case_id = metadata.get("case_number", file_id)
            case_title = metadata.get("case_title", "Unknown")
            file_hash = doc.meta.get("file_hash", "")
            original_filename = doc.meta.get("original_filename", "")
            ingestion_timestamp = doc.meta.get("ingestion_timestamp", datetime.now().isoformat())
            
            # Get embeddings
            metadata_embedding = doc.meta.get("metadata_embedding", [])
            case_facts_embedding = doc.meta.get("case_facts_embedding", [])
            issues_embedding = doc.meta.get("issues_embedding", [])
            evidence_embedding = doc.meta.get("evidence_embedding", [])
            arguments_embedding = doc.meta.get("arguments_embedding", [])
            reasoning_embedding = doc.meta.get("reasoning_embedding", [])
            judgement_embedding = doc.meta.get("judgement_embedding", [])
            facts_embedding = doc.meta.get("facts_embedding", [])
            
            # Get factual summary
            factual_summary = doc.meta.get("factual_summary", {})
            
            # Connect to database
            conn = psycopg2.connect(self.conn_str)
            cursor = conn.cursor()
            
            # Insert into legal_cases table
            cursor.execute("""
                INSERT INTO legal_cases (
                    file_id, case_id, case_title, file_hash, original_filename, ingestion_timestamp,
                    summary,
                    metadata_embedding, case_facts_embedding, issues_embedding, evidence_embedding,
                    arguments_embedding, reasoning_embedding, judgement_embedding,
                    factual_summary, facts_embedding
                ) VALUES (
                    %s, %s, %s, %s, %s, %s,
                    %s,
                    %s, %s, %s, %s, %s, %s, %s,
                    %s, %s
                )
                ON CONFLICT (file_id) DO UPDATE
                SET case_id = EXCLUDED.case_id,
                    case_title = EXCLUDED.case_title,
                    summary = EXCLUDED.summary,
                    metadata_embedding = EXCLUDED.metadata_embedding,
                    case_facts_embedding = EXCLUDED.case_facts_embedding,
                    issues_embedding = EXCLUDED.issues_embedding,
                    evidence_embedding = EXCLUDED.evidence_embedding,
                    arguments_embedding = EXCLUDED.arguments_embedding,
                    reasoning_embedding = EXCLUDED.reasoning_embedding,
                    judgement_embedding = EXCLUDED.judgement_embedding,
                    factual_summary = EXCLUDED.factual_summary,
                    facts_embedding = EXCLUDED.facts_embedding;
            """, (
                file_id, case_id, case_title, file_hash, original_filename, ingestion_timestamp,
                Json(summary),
                metadata_embedding, case_facts_embedding, issues_embedding, evidence_embedding,
                arguments_embedding, reasoning_embedding, judgement_embedding,
                Json(factual_summary), facts_embedding
            ))
            
            conn.commit()
            cursor.close()
            conn.close()
            
            logger.info(f"Successfully wrote case to legal_cases table: {case_id}")
            return {"documents": [doc], "success": True}
            
        except Exception as e:
            logger.error(f"Failed to write to legal_cases table: {e}")
            return {"documents": [], "success": False}


@component
class LegalCasesDuplicateCheckNode:
    """
    Checks for duplicates in legal_cases table using file_hash.
    """
    
    def __init__(self, db_config: Dict[str, str]):
        """
        Initialize duplicate checker for legal_cases table.
        
        Args:
            db_config: Database configuration dict
        """
        self.db_config = db_config
        self.conn_str = f"postgresql://{db_config['user']}:{db_config['password']}@{db_config['host']}:{db_config['port']}/{db_config['database']}"
        logger.info("LegalCasesDuplicateCheckNode initialized")
    
    @component.output_types(documents=List[Document], is_duplicate=bool, existing_case=dict)
    def run(self, documents: List[Document]) -> dict:
        """
        Check if document exists in legal_cases table by file_hash.
        
        Args:
            documents: List of Haystack Documents
            
        Returns:
            dict with documents, is_duplicate flag, and existing_case data if duplicate
        """
        if not documents:
            return {"documents": [], "is_duplicate": False, "existing_case": None}
        
        doc = documents[0]
        file_hash = doc.meta.get("file_hash")
        
        if not file_hash:
            logger.warning("No file_hash in document metadata, cannot check for duplicates")
            return {"documents": documents, "is_duplicate": False, "existing_case": None}
        
        try:
            conn = psycopg2.connect(self.conn_str)
            cursor = conn.cursor()
            
            # Check if document with this file_hash already exists and retrieve its data
            cursor.execute("""
                SELECT file_id, case_id, case_title, summary, factual_summary
                FROM legal_cases 
                WHERE file_hash = %s
                LIMIT 1
            """, (file_hash,))
            
            existing = cursor.fetchone()
            cursor.close()
            conn.close()
            
            if existing:
                logger.info(f"Duplicate found with file_hash: {file_hash}")
                
                # Parse existing case data
                file_id, case_id, case_title, summary_json, factual_summary_json = existing
                
                existing_case = {
                    "file_id": file_id,
                    "case_id": case_id,
                    "case_title": case_title,
                    "summary": summary_json,
                    "factual_summary": factual_summary_json
                }
                
                return {"documents": [], "is_duplicate": True, "existing_case": existing_case}
            else:
                logger.info("No duplicate found")
                return {"documents": documents, "is_duplicate": False, "existing_case": None}
                
        except Exception as e:
            logger.error(f"Error checking for duplicates: {e}")
            return {"documents": documents, "is_duplicate": False, "existing_case": None}
