"""
Legal Case Similarity Search Pipeline
Complete pipeline from PDF to finding similar cases with threshold-based cross-encoder filtering.

Steps:
1. Load the given PDF
2. Convert it to markdown  
3. Extract metadata
4. Select appropriate template
5. Load template
6. Extract facts
7. Form vector embedding
8. Load stored vector embeddings
9. Construct similarity using cosine similarity
10. Take top k similar cases (excluding duplicates)
11. Re-rank top k cases using cross-encoder and filter by threshold
12. Display cases with cross-encoder scores above threshold
"""

import os
import sys
import logging
import json
import numpy as np
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from dotenv import load_dotenv
from sklearn.metrics.pairwise import cosine_similarity
from sentence_transformers import SentenceTransformer, CrossEncoder

from raw_code.bg_creation.convert_pdf_to_md import PDFToMarkdownConverter

# Add the bg_creation directory to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'bg_creation'))


from raw_code.bg_creation.extract_metadata import MetadataExtractor, CaseMetadata
from raw_code.bg_creation.ontology_matcher import OntologyMatcher, MatchResult
from raw_code.bg_creation.load_template import TemplateLoader, Template
from raw_code.bg_creation.extract_facts import FactExtractor
from raw_code.bg_creation.case_embedder import CaseEmbedder

# Load environment variables
load_dotenv()

class SimilarityCaseSearchPipeline:
    """
    Complete pipeline for finding similar legal cases from a new PDF document.
    """
    
    def __init__(self, config_path: str = "config.json"):
        """
        Initialize the similarity search pipeline.
        
        Args:
            config_path (str): Path to configuration file
        """
        self.logger = logging.getLogger(__name__)
        self.setup_logging()
        
        # Load configuration
        self.config = self.load_config(config_path)
        
        # Get TOP_K from environment variable, default to 5
        self.top_k = int(os.getenv('TOP_K_SIMILAR_CASES', '5'))
        self.logger.info(f"Top K similar cases set to: {self.top_k}")
        
        # Get cross-encoder configuration
        self.cross_encoder_model_name = os.getenv('CROSS_ENCODER_MODEL', 'cross-encoder/ms-marco-MiniLM-L6-v2')
        self.cross_encoder_threshold = float(os.getenv('CROSS_ENCODER_THRESHOLD', '0.0'))
        self.logger.info(f"Cross-encoder model: {self.cross_encoder_model_name}")
        self.logger.info(f"Cross-encoder threshold: {self.cross_encoder_threshold}")
        
        # Initialize pipeline components
        self.pdf_converter = PDFToMarkdownConverter(self.config)
        self.metadata_extractor = MetadataExtractor(self.config.get('openai_api_key'))
        self.ontology_matcher = OntologyMatcher(self.config.get('ontology_path', 'Ontology_schema/ontology_schema.json'))
        self.template_loader = TemplateLoader(self.config.get('templates_dir', 'templates'))
        self.fact_extractor = FactExtractor(self.config.get('openai_api_key'))
        
        # Initialize embedder
        embedding_model = self.config.get('embedding_model', 'all-mpnet-base-v2')
        embedding_output_dir = self.config.get('embedding_output_dir', 'Embedding results')
        self.case_embedder = CaseEmbedder(model_name=embedding_model, output_dir=embedding_output_dir)
        
        # Initialize SentenceTransformer model for similarity computation
        self.similarity_model = SentenceTransformer(embedding_model)
        
        # Initialize CrossEncoder model for re-ranking (lazy loading)
        self.cross_encoder = None
        
        # Storage for loaded embeddings
        self.existing_embeddings = None
        self.existing_case_ids = None
        self.existing_metadata = None
        
    def setup_logging(self):
        """Setup logging configuration with reduced noise."""
        # Check if logging should be disabled via environment variable
        disable_logging = os.getenv('DISABLE_LOGGING', 'false').lower() in ('true', '1', 'yes', 'on')
        
        if disable_logging:
            # Disable all logging by setting to CRITICAL level (highest)
            logging.basicConfig(level=logging.CRITICAL)
            self.logger.setLevel(logging.CRITICAL)
            # Disable all specific loggers
            logging.getLogger('extract_metadata').setLevel(logging.CRITICAL)
            logging.getLogger('ontology_matcher').setLevel(logging.CRITICAL)
            logging.getLogger('load_template').setLevel(logging.CRITICAL)
            return
        
        # Set up main logger
        logging.basicConfig(
            level=logging.WARNING,  # Only show warnings and errors by default
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler()
            ]
        )
        
        # Set specific loggers to WARNING to reduce noise
        logging.getLogger('extract_metadata').setLevel(logging.WARNING)
        logging.getLogger('ontology_matcher').setLevel(logging.WARNING)
        logging.getLogger('load_template').setLevel(logging.WARNING)
        logging.getLogger('extract_facts').setLevel(logging.WARNING)
        logging.getLogger('case_embedder').setLevel(logging.WARNING)
        logging.getLogger('sentence_transformers').setLevel(logging.WARNING)
        logging.getLogger('httpx').setLevel(logging.WARNING)
        logging.getLogger('convert_pdf_to_md').setLevel(logging.WARNING)
        
        # Keep our main pipeline logger at INFO level
        self.logger.setLevel(logging.INFO)
    
    def load_config(self, config_path: str) -> Dict[str, Any]:
        """
        Load configuration from JSON file.
        
        Args:
            config_path (str): Path to config file
            
        Returns:
            Dict[str, Any]: Configuration dictionary
        """
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            # Override with environment variables if present
            if os.getenv('OPENAI_API_KEY'):
                config['openai_api_key'] = os.getenv('OPENAI_API_KEY')
                
            return config
        except Exception as e:
            self.logger.error(f"Failed to load config from {config_path}: {e}")
            return {}
    
    def step1_load_pdf(self, pdf_path: str) -> str:
        """
        Step 1: Load the given PDF file.
        
        Args:
            pdf_path (str): Path to PDF file
            
        Returns:
            str: Path to PDF file (validated)
        """
        self.logger.info(f"Step 1: Loading PDF file: {pdf_path}")
        
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")
        
        if not pdf_path.lower().endswith('.pdf'):
            raise ValueError(f"File is not a PDF: {pdf_path}")
        
        self.logger.info(f"Step 1 completed: PDF file loaded successfully")
        return pdf_path
    
    def step2_convert_to_markdown(self, pdf_path: str) -> str:
        """
        Step 2: Convert PDF to markdown.
        
        Args:
            pdf_path (str): Path to PDF file
            
        Returns:
            str: Extracted markdown text
        """
        self.logger.info(f"Step 2: Converting PDF to markdown")
        
        try:
            # Extract text from PDF
            raw_text = self.pdf_converter.extract_text_from_pdf(pdf_path)
            
            # Clean the text
            markdown_text = self.pdf_converter.clean_text(raw_text)
            
            self.logger.info(f"Step 2 completed: PDF converted to markdown ({len(markdown_text)} characters)")
            return markdown_text
            
        except Exception as e:
            self.logger.error(f"Failed to convert PDF to markdown: {e}")
            raise
    
    def step3_to_6_extract_metadata_and_facts(self, markdown_text: str, file_path: str = "") -> Dict[str, Any]:
        """
        Steps 3-6: Extract metadata, select template, load template, and extract facts.
        
        Args:
            markdown_text (str): Markdown text content
            file_path (str): Path to the original case file for fallback inference
            
        Returns:
            Dict[str, Any]: Complete extraction result with facts
        """
        self.logger.info(f"Steps 3-6: Running complete extraction pipeline")
        
        try:
            # Use the integrated extraction method from the original pipeline
            extraction_result = self.metadata_extractor.extract_metadata_and_facts(markdown_text, file_path)
            
            if 'error' in extraction_result:
                raise ValueError(f"Extraction failed: {extraction_result['error']}")
            
            self.logger.info(f"Steps 3-6 completed: Complete extraction finished")
            self.logger.info(f"   Case Title: {extraction_result['metadata'].get('case_title', 'Unknown')}")
            self.logger.info(f"   Court: {extraction_result['metadata'].get('court_name', 'Unknown')}")
            self.logger.info(f"   Date: {extraction_result['metadata'].get('judgment_date', 'Unknown')}")
            self.logger.info(f"   Template: {extraction_result.get('template_label', 'Unknown')}")
            self.logger.info(f"   Confidence: {extraction_result.get('confidence_score', 0):.3f}")
            
            return extraction_result
            
        except Exception as e:
            self.logger.error(f"Failed to extract metadata and facts: {e}")
            raise
    

    def step7_form_vector_embedding(self, extraction_result: Dict[str, Any], case_id: str = None) -> np.ndarray:
        """
        Step 7: Form vector embedding from extracted facts.
        
        Args:
            extraction_result (Dict[str, Any]): Complete extraction result
            case_id (str): Case identifier
            
        Returns:
            np.ndarray: Vector embedding
        """
        self.logger.info(f"Step 7: Forming vector embedding")
        
        try:
            if case_id is None:
                case_id = f"new_case_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            # Get the extracted facts from the result
            facts = extraction_result['extracted_facts']
            
            if not facts:
                raise ValueError("No extracted facts found in extraction result")
            
            # Print the template structure that will be embedded
            # print("\n" + "="*80)
            # print("TEMPLATE BEING EMBEDDED")
            # print("="*80)
            
            # print(f"Template ID: {extraction_result.get('template_used', 'Unknown')}")
            # print(f"Template Label: {extraction_result.get('template_label', 'Unknown')}")
            # print(f"Extraction Confidence: {extraction_result.get('confidence_score', 0):.3f}")
            
            # print("\nExtracted Facts Structure:")
            # print(json.dumps(facts, indent=2, ensure_ascii=False))
            
            # print("="*80)
            
            # Generate embedding using case embedder
            embedding_result = self.case_embedder.embed_case(facts, case_id)
            embedding = embedding_result['embedding']
            
            # Store the case_id for later use in filtering
            self._last_case_id_used = case_id
            
            self.logger.info(f"Step 7 completed: Vector embedding formed")
            self.logger.info(f"   Embedding dimension: {len(embedding)}")
            self.logger.info(f"   Case ID: {case_id}")
            
            return embedding
            
        except Exception as e:
            self.logger.error(f"Failed to form vector embedding: {e}")
            raise
    
    def step8_load_stored_embeddings(self, embeddings_dir: str = "Embedding results") -> Tuple[np.ndarray, List[str], Dict]:
        """
        Step 8: Load stored vector embeddings.
        
        Args:
            embeddings_dir (str): Directory containing stored embeddings
            
        Returns:
            Tuple[np.ndarray, List[str], Dict]: Embeddings array, case IDs, and metadata
        """
        self.logger.info(f"Step 8: Loading stored vector embeddings")
        
        try:
            embeddings_path = Path(embeddings_dir)
            
            # Find the most recent embeddings file
            npz_files = list(embeddings_path.glob("*.npz"))
            if not npz_files:
                raise FileNotFoundError(f"No embedding files found in {embeddings_dir}")
            
            # Sort by modification time and get the most recent
            latest_npz = max(npz_files, key=os.path.getmtime)
            
            # Find corresponding metadata file
            npz_name = latest_npz.stem
            metadata_files = list(embeddings_path.glob(f"*metadata*{npz_name.split('_')[-1]}.json"))
            metadata_file = metadata_files[0] if metadata_files else None
            
            self.logger.info(f"Loading embeddings from: {latest_npz}")
            if metadata_file:
                self.logger.info(f"Loading metadata from: {metadata_file}")
            
            # Load embeddings using case embedder
            self.case_embedder.load_embeddings(str(latest_npz), str(metadata_file) if metadata_file else None)
            
            # Extract embeddings and case IDs
            case_ids = list(self.case_embedder.case_embeddings.keys())
            embeddings = np.array([self.case_embedder.case_embeddings[cid]['embedding'] for cid in case_ids])
            
            # Load metadata
            metadata = {}
            if metadata_file:
                with open(metadata_file, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
            
            # Store for later use
            self.existing_embeddings = embeddings
            self.existing_case_ids = case_ids
            self.existing_metadata = metadata
            
            self.logger.info(f"Step 8 completed: Loaded embeddings for {len(case_ids)} cases")
            
            return embeddings, case_ids, metadata
            
        except Exception as e:
            self.logger.error(f"Failed to load stored embeddings: {e}")
            raise
    
    def step9_compute_similarity(self, new_embedding: np.ndarray, existing_embeddings: np.ndarray, case_ids: List[str] = None) -> np.ndarray:
        """
        Step 9: Compute similarity between new case and existing cases.
        
        Args:
            new_embedding (np.ndarray): New case embedding
            existing_embeddings (np.ndarray): Existing case embeddings
            case_ids (List[str]): List of existing case IDs for display
            
        Returns:
            np.ndarray: Similarity scores
        """
        self.logger.info(f"Step 9: Computing similarity scores")
        
        try:
            # Reshape new embedding for SentenceTransformer similarity computation
            new_embedding = new_embedding.reshape(1, -1)
            
            # Compute similarity using SentenceTransformer model
            similarities = self.similarity_model.similarity(new_embedding, existing_embeddings)[0]
            
            # Convert tensor to numpy array if needed
            if hasattr(similarities, 'numpy'):
                similarities = similarities.numpy()
            
            # Print similarity matrix
            # print("\n" + "="*80)
            # print("SIMILARITY MATRIX (TENSOR)")
            # print("="*80)
            # print(f"Input case vs. {len(similarities)} existing cases")
            # print(f"Similarity range: [{similarities.min():.4f}, {similarities.max():.4f}]")
            # print(f"Mean similarity: {similarities.mean():.4f}")
            # print(f"Standard deviation: {similarities.std():.4f}")
            
            # Print top 10 similarities with case names
            # print(f"\nTop 10 Highest Similarities:")
            # print("-" * 50)
            
            # # Get sorted indices
            # sorted_indices = np.argsort(similarities)[::-1]
            
            # for i, idx in enumerate(sorted_indices[:10]):
            #     case_name = case_ids[idx] if case_ids else f"Case_{idx}"
            #     # Truncate long case names for better display
            #     display_name = case_name[:50] + "..." if len(case_name) > 50 else case_name
            #     print(f"{i+1:2d}. {similarities[idx]:.4f} - {display_name}")
            
            # Print full similarity array (truncated if too long)
            # print(f"\nComplete Similarity Vector:")
            # print("-" * 30)
            # if len(similarities) <= 20:
            #     # Print all if small enough
            #     for i, sim in enumerate(similarities):
            #         case_name = case_ids[i] if case_ids else f"Case_{i}"
            #         display_name = case_name[:30] + "..." if len(case_name) > 30 else case_name
            #         print(f"[{i:2d}] {sim:.4f} - {display_name}")
            # else:
            #     # Print first 10 and last 5
            #     print("First 10 cases:")
            #     for i in range(10):
            #         case_name = case_ids[i] if case_ids else f"Case_{i}"
            #         display_name = case_name[:30] + "..." if len(case_name) > 30 else case_name
            #         print(f"[{i:2d}] {similarities[i]:.4f} - {display_name}")
                
            #     print("...")
            #     print(f"Last 5 cases:")
            #     for i in range(len(similarities)-5, len(similarities)):
            #         case_name = case_ids[i] if case_ids else f"Case_{i}"
            #         display_name = case_name[:30] + "..." if len(case_name) > 30 else case_name
            #         print(f"[{i:2d}] {similarities[i]:.4f} - {display_name}")
            
            # print("="*80)
            
            self.logger.info(f"Step 9 completed: Computed similarity with {len(similarities)} cases")
            self.logger.info(f"   Similarity range: [{similarities.min():.3f}, {similarities.max():.3f}]")
            
            return similarities
            
        except Exception as e:
            self.logger.error(f"Failed to compute similarity: {e}")
            raise
    
    def step10_get_top_k_similar(self, similarities: np.ndarray, case_ids: List[str], k: int = None, 
                                test_case_id: str = None, input_pdf_path: str = None) -> List[Tuple[str, float]]:
        """
        Step 10: Get top-k most similar cases, excluding the test case itself and exact duplicates.
        
        Args:
            similarities (np.ndarray): Similarity scores
            case_ids (List[str]): Case IDs corresponding to similarity scores
            k (int): Number of top similar cases to return
            test_case_id (str): ID of the current test case to exclude
            input_pdf_path (str): Path to input PDF to help identify duplicates
            
        Returns:
            List[Tuple[str, float]]: List of (case_id, similarity_score) tuples
        """
        if k is None:
            k = self.top_k
            
        self.logger.info(f"Step 10: Getting top {k} most similar cases (excluding duplicates)")
        
        try:
            # Sort all cases by similarity (descending)
            sorted_indices = np.argsort(similarities)[::-1]
            
            # Extract case name from input PDF path for comparison
            input_case_name = None
            if input_pdf_path:
                from pathlib import Path
                input_case_name = Path(input_pdf_path).stem.lower()
            
            # Filter out duplicates and test case
            filtered_cases = []
            excluded_count = 0
            
            for idx in sorted_indices:
                case_id = case_ids[idx]
                similarity_score = similarities[idx]
                
                # Skip if this is the test case itself (generated case ID)
                if test_case_id and case_id == test_case_id:
                    excluded_count += 1
                    self.logger.info(f"   Excluded test case: {case_id} (similarity: {similarity_score:.4f})")
                    continue
                
                # Skip if similarity is too high (indicating duplicate/same case)
                # Threshold of 0.99 to catch near-identical cases
                if similarity_score >= 0.99:
                    excluded_count += 1
                    self.logger.info(f"   Excluded duplicate case: {case_id} (similarity: {similarity_score:.4f})")
                    continue
                
                # Skip if the case name matches the input PDF name (same original case)
                if input_case_name:
                    case_name_lower = case_id.lower().replace('_', ' ').replace('vs.', 'vs').replace('  ', ' ')
                    input_name_clean = input_case_name.replace('_', ' ').replace('vs.', 'vs').replace('  ', ' ')
                    
                    if input_name_clean in case_name_lower or case_name_lower in input_name_clean:
                        excluded_count += 1
                        self.logger.info(f"   Excluded same case: {case_id} (similarity: {similarity_score:.4f})")
                        continue
                
                # Add to filtered results
                filtered_cases.append((case_id, similarity_score))
                
                # Stop once we have enough cases
                if len(filtered_cases) >= k:
                    break
            
            self.logger.info(f"Step 10 completed: Found {len(filtered_cases)} similar cases (excluded {excluded_count} duplicates)")
            
            return filtered_cases
            
        except Exception as e:
            self.logger.error(f"Failed to get top-k similar cases: {e}")
            raise
    
    def _load_cross_encoder(self):
        """Load cross-encoder model lazily."""
        if self.cross_encoder is None:
            self.logger.info(f"Loading cross-encoder model: {self.cross_encoder_model_name}")
            self.cross_encoder = CrossEncoder(self.cross_encoder_model_name)
        return self.cross_encoder
    
    def _extract_facts_as_text(self, facts_dict: Dict[str, Any]) -> str:
        """
        Extract fact values from a facts dictionary and concatenate them.
        
        Args:
            facts_dict (Dict[str, Any]): Dictionary containing extracted facts
            
        Returns:
            str: Concatenated fact values separated by ". "
        """
        if not facts_dict:
            return ""
        
        fact_values = []
        
        def extract_values_recursive(obj):
            """Recursively extract string values from nested dictionary/list structures."""
            if isinstance(obj, dict):
                for value in obj.values():
                    extract_values_recursive(value)
            elif isinstance(obj, list):
                for item in obj:
                    extract_values_recursive(item)
            elif isinstance(obj, str) and obj.strip():
                # Only add non-empty strings
                fact_values.append(obj.strip())
        
        extract_values_recursive(facts_dict)
        
        # Join with ". " and ensure proper sentence ending
        result = ". ".join(fact_values)
        if result and not result.endswith('.'):
            result += "."
        
        return result
    
    def _load_case_facts(self, case_id: str) -> Dict[str, Any]:
        """
        Load facts for a specific case from the extracted files.
        
        Args:
            case_id (str): Case identifier
            
        Returns:
            Dict[str, Any]: Case facts dictionary
        """
        try:
            # Try to find the case file in the extracted directory
            cases_dir = Path("cases/extracted")
            
            # Look for files that match the case_id
            possible_files = [
                cases_dir / f"{case_id}_facts.json",
                cases_dir / f"{case_id}.json"
            ]
            
            # Also try direct match
            for file_path in cases_dir.glob("*.json"):
                if case_id in file_path.stem:
                    possible_files.append(file_path)
            
            for file_path in possible_files:
                if file_path.exists():
                    with open(file_path, 'r', encoding='utf-8') as f:
                        return json.load(f)
            
            # If not found in files, try to get from metadata
            if self.existing_metadata and 'case_texts' in self.existing_metadata:
                case_text = self.existing_metadata['case_texts'].get(case_id, '')
                if case_text:
                    return json.loads(case_text)
            
            self.logger.warning(f"Could not load facts for case: {case_id}")
            return {}
            
        except Exception as e:
            self.logger.warning(f"Error loading facts for case {case_id}: {e}")
            return {}
    
    def step11_cross_encoder_rerank(self, top_k_cases: List[Tuple[str, float]], 
                                  input_facts: Dict[str, Any]) -> List[Tuple[str, float, float]]:
        """
        Step 11: Re-rank top-k cases using cross-encoder and filter by threshold.
        
        Args:
            top_k_cases (List[Tuple[str, float]]): Top-k similar cases from cosine similarity
            input_facts (Dict[str, Any]): Facts from the input case
            
        Returns:
            List[Tuple[str, float, float]]: Cases above threshold with (case_id, cosine_similarity, cross_encoder_score)
        """
        self.logger.info(f"Step 11: Re-ranking top {len(top_k_cases)} cases using cross-encoder with threshold {self.cross_encoder_threshold}")
        
        try:
            # Load cross-encoder model
            cross_encoder = self._load_cross_encoder()
            
            # Extract input case facts as text
            input_text = self._extract_facts_as_text(input_facts)
            
            if not input_text:
                self.logger.warning("No facts extracted from input case, skipping cross-encoder re-ranking")
                # Return original results with dummy cross-encoder scores, apply threshold to cosine similarity
                filtered_results = [(case_id, cos_sim, cos_sim) for case_id, cos_sim in top_k_cases if cos_sim > self.cross_encoder_threshold]
                return filtered_results
            
            self.logger.info(f"Input case facts text length: {len(input_text)} characters")
            
            # Prepare passages for cross-encoder
            passages = []
            case_info = []
            
            for case_id, cosine_sim in top_k_cases:
                # Load case facts
                case_facts = self._load_case_facts(case_id)
                case_text = self._extract_facts_as_text(case_facts)
                
                if case_text:
                    passages.append(case_text)
                    case_info.append((case_id, cosine_sim, len(case_text)))
                else:
                    # If no facts found, use case_id as fallback
                    passages.append(case_id.replace('_', ' '))
                    case_info.append((case_id, cosine_sim, 0))
                    self.logger.warning(f"No facts found for case {case_id}, using case name as fallback")
            
            if not passages:
                self.logger.warning("No passages found for cross-encoder, returning original results")
                filtered_results = [(case_id, cos_sim, cos_sim) for case_id, cos_sim in top_k_cases if cos_sim > self.cross_encoder_threshold]
                return filtered_results
            
            # Print cross-encoder input information
            # print("\n" + "="*80)
            # print("CROSS-ENCODER RE-RANKING")
            # print("="*80)
            # print(f"Query (Input Case Facts): {input_text[:200]}{'...' if len(input_text) > 200 else ''}")
            # print(f"Number of passages to rank: {len(passages)}")
            # print(f"Threshold for similarity: {self.cross_encoder_threshold}")
            # print("-" * 40)
            
            # Use cross-encoder to rank passages
            ranks = cross_encoder.rank(input_text, passages)
            
            # Prepare results with both similarity scores and apply threshold filtering
            cross_encoder_results = []
            filtered_results = []
            
            # print("Cross-Encoder Ranking Results:")
            for i, rank in enumerate(ranks):
                passage_idx = rank['corpus_id']
                cross_encoder_score = rank['score']
                case_id, cosine_sim, text_length = case_info[passage_idx]
                
                cross_encoder_results.append((case_id, cosine_sim, cross_encoder_score))
                
                # Display ranking information
                display_name = case_id.replace('_', ' ')[:60]
                if len(case_id) > 60:
                    display_name += "..."
                
                status = "ABOVE THRESHOLD" if cross_encoder_score > self.cross_encoder_threshold else "✗ BELOW THRESHOLD"
                # print(f"{i+1:2d}. {display_name} [{status}]")
                # print(f"    Cross-Encoder Score: {cross_encoder_score:.4f}")
                # print(f"    Cosine Similarity: {cosine_sim:.4f}")
                # print(f"    Facts Text Length: {text_length} chars")
                
                # Apply threshold filtering
                if cross_encoder_score > self.cross_encoder_threshold:
                    filtered_results.append((case_id, cosine_sim, cross_encoder_score))
                # print()
            
            # print("="*80)
            # print(f"THRESHOLD FILTERING RESULTS:")
            # print(f"Total cases ranked: {len(cross_encoder_results)}")
            # print(f"Cases above threshold ({self.cross_encoder_threshold}): {len(filtered_results)}")
            # print("="*80)
            
            self.logger.info(f"Step 11 completed: Re-ranked {len(top_k_cases)} cases, {len(filtered_results)} cases above threshold")
            
            return filtered_results
            
        except Exception as e:
            self.logger.error(f"Failed to re-rank with cross-encoder: {e}")
            # Fallback to original results with threshold applied to cosine similarity
            self.logger.info("Falling back to cosine similarity results with threshold filtering")
            filtered_results = [(case_id, cos_sim, cos_sim) for case_id, cos_sim in top_k_cases if cos_sim > self.cross_encoder_threshold]
            return filtered_results
    
    def display_input_case_summary(self, extraction_result: Dict[str, Any]) -> None:
        """
        Display the input case summary and metadata before similarity analysis.
        
        Args:
            extraction_result (Dict[str, Any]): Complete extraction result with facts and metadata
        """
        print("\n" + "="*80)
        print("INPUT CASE SUMMARY & METADATA")
        print("="*80)
        
        # Display case metadata
        metadata = extraction_result.get('metadata', {})
        print("\nCASE METADATA:")
        print("-" * 40)
        print(f"📋 Case Title: {metadata.get('case_title', 'Unknown')}")
        print(f"🏛️  Court: {metadata.get('court_name', 'Unknown')}")
        print(f"📅 Date: {metadata.get('judgment_date', 'Unknown')}")
        print(f"📝 Template Used: {extraction_result.get('template_label', 'Unknown')}")
        print(f"🎯 Template ID: {extraction_result.get('template_used', 'Unknown')}")
        print(f"📊 Matching Confidence: {extraction_result.get('confidence_score', 0):.3f}")
        
        # Display legal sections if available
        sections = metadata.get('sections_invoked', [])
        if sections:
            if isinstance(sections, str):
                print(f"⚖️  Legal Sections: {sections}")
            elif isinstance(sections, list):
                print(f"⚖️  Legal Sections: {', '.join(sections)}")
        
        # Display most appropriate section
        most_appropriate = metadata.get('most_appropriate_section', 'Unknown')
        if most_appropriate and most_appropriate != 'Unknown':
            print(f"📌 Primary Section: {most_appropriate}")
        
        # Extract and display case summary (concatenation of all extracted facts)
        extracted_facts = extraction_result.get('extracted_facts', {})
        if extracted_facts:
            case_summary = self._extract_facts_as_text(extracted_facts)
            if case_summary:
                print("\nCASE FACTS SUMMARY:")
                print("-" * 40)
                # Display full summary without truncation
                print(f"📄 {case_summary}")
                print(f"\n[Full summary length: {len(case_summary)} characters]")
            else:
                print("\nCASE FACTS SUMMARY:")
                print("-" * 40)
                print("📄 No facts summary could be extracted")
        else:
            print("\nCASE FACTS SUMMARY:")
            print("-" * 40)
            print("📄 No extracted facts available")
        
        print("\n" + "="*80)
        print("PROCEEDING WITH SIMILARITY ANALYSIS...")
        print("="*80)
    
    def step12_display_results(self, filtered_cases: List[Tuple[str, float, float]]) -> None:
        """
        Step 12: Display cases that passed the cross-encoder threshold filtering.
        
        Args:
            filtered_cases (List[Tuple[str, float, float]]): Cases above threshold with (case_id, cosine_sim, cross_encoder_score)
        """
        self.logger.info(f"Step 12: Displaying final results")
        
        print("\n" + "="*80)
        print("FINAL ANALYSIS RESULTS")
        print("="*80)
        
        # Display template information if available
        if hasattr(self, '_extraction_result') and self._extraction_result:
            extraction_result = self._extraction_result
            print("\nINPUT CASE ANALYSIS:")
            print(f"  Case Title: {extraction_result['metadata'].get('case_title', 'Unknown')}")
            print(f"  Court: {extraction_result['metadata'].get('court_name', 'Unknown')}")
            print(f"  Date: {extraction_result['metadata'].get('judgment_date', 'Unknown')}")
            print(f"  Template Used: {extraction_result.get('template_label', 'Unknown')}")
            print(f"  Template ID: {extraction_result.get('template_used', 'Unknown')}")
            print(f"  Matching Confidence: {extraction_result.get('confidence_score', 0):.3f}")
            
            # Display sections if available
            if 'metadata' in extraction_result and 'sections_invoked' in extraction_result['metadata']:
                sections = extraction_result['metadata']['sections_invoked']
                if sections:
                    print(f"  Legal Sections: {', '.join(sections)}")
            
            # Display most appropriate section
            if 'metadata' in extraction_result and 'most_appropriate_section' in extraction_result['metadata']:
                most_appropriate = extraction_result['metadata']['most_appropriate_section']
                if most_appropriate:
                    print(f"  Primary Section: {most_appropriate}")
        
        if filtered_cases:
            print(f"\n{len(filtered_cases)} SIMILAR LEGAL CASES (ABOVE THRESHOLD {self.cross_encoder_threshold}):")
            print("-" * 80)
            
            for i, (case_id, cosine_similarity, cross_encoder_score) in enumerate(filtered_cases, 1):
                # Clean up case name for display
                display_name = case_id.replace('_', ' ').title()
                
                print(f"{i:2d}. {display_name}")
                print(f"    Cross-Encoder Score: {cross_encoder_score:.4f}")
                print(f"    Cosine Similarity: {cosine_similarity:.4f}")
                
                # Load case facts and display summary
                case_facts = self._load_case_facts(case_id)
                if case_facts:
                    case_summary = self._extract_facts_as_text(case_facts)
                    if case_summary:
                        # Truncate very long summaries for better readability
                        max_summary_length = 500
                        if len(case_summary) > max_summary_length:
                            case_summary = case_summary[:max_summary_length] + "..."
                        print(f"    Summary: {case_summary}")
                    else:
                        print("    Summary: No facts summary available")
                else:
                    print("    Summary: Unable to load case facts")
                
                # Try to get additional metadata if available
                if self.existing_metadata and 'case_texts' in self.existing_metadata:
                    case_text = self.existing_metadata['case_texts'].get(case_id, '')
                    if case_text:
                        try:
                            case_data = json.loads(case_text)
                            if 'tier_4_procedural' in case_data:
                                procedural = case_data['tier_4_procedural']
                                if 'case_title' in procedural:
                                    print(f"    Case Title: {procedural['case_title']}")
                                if 'court_name' in procedural:
                                    print(f"    Court: {procedural['court_name']}")
                                if 'judgment_date' in procedural:
                                    print(f"    Date: {procedural['judgment_date']}")
                        except:
                            pass
                
                print()
        else:
            print(f"\nNO CASES FOUND ABOVE THRESHOLD ({self.cross_encoder_threshold})")
            print("Consider lowering the threshold or reviewing the input case.")
            print("-" * 80)
        
        print("="*80)
        self.logger.info(f"Step 12 completed: Final results displayed")
    
    def run_complete_pipeline(self, pdf_path: str, case_id: str = None) -> List[Tuple[str, float, float]]:
        """
        Run the complete similarity search pipeline with cross-encoder re-ranking.
        
        Args:
            pdf_path (str): Path to input PDF file
            case_id (str): Optional case identifier
            
        Returns:
            List[Tuple[str, float, float]]: Cases above threshold with (case_id, cosine_sim, cross_encoder_score)
        """
        self.logger.info(f"Starting Complete Similarity Search Pipeline")
        self.logger.info(f"Input PDF: {pdf_path}")
        self.logger.info(f"Top K: {self.top_k}")
        self.logger.info(f"Cross-encoder threshold: {self.cross_encoder_threshold}")
        # print("\n" + "="*80)
        # print("LEGAL CASE SIMILARITY SEARCH PIPELINE")
        # print("="*80)
        
        try:
            # Step 1: Load PDF
            validated_pdf_path = self.step1_load_pdf(pdf_path)
            
            # Step 2: Convert to markdown
            markdown_text = self.step2_convert_to_markdown(validated_pdf_path)
            
            # Steps 3-6: Extract metadata, template matching, and facts (combined)
            extraction_result = self.step3_to_6_extract_metadata_and_facts(markdown_text, validated_pdf_path)
            
            # Store extraction result for display
            self._extraction_result = extraction_result
            
            # Step 7: Form vector embedding
            new_embedding = self.step7_form_vector_embedding(extraction_result, case_id)
            
            # Step 8: Load stored vector embeddings
            existing_embeddings, existing_case_ids, metadata_dict = self.step8_load_stored_embeddings()
            
            # Display input case summary before similarity analysis
            self.display_input_case_summary(extraction_result)
            
            # Step 9: Compute similarity
            similarities = self.step9_compute_similarity(new_embedding, existing_embeddings, existing_case_ids)
            
            # Step 10: Get top-k similar cases (excluding duplicates)
            # Get the actual case ID that was used for embedding
            actual_case_id = getattr(self, '_last_case_id_used', None)
            top_k_cases = self.step10_get_top_k_similar(similarities, existing_case_ids, 
                                                      test_case_id=actual_case_id, 
                                                      input_pdf_path=pdf_path)
            
            # Step 11: Cross-encoder re-ranking with threshold filtering
            input_facts = extraction_result.get('extracted_facts', {})
            filtered_cases = self.step11_cross_encoder_rerank(top_k_cases, input_facts)
            
            # Step 12: Display final results
            self.step12_display_results(filtered_cases)
            
            self.logger.info(f"Pipeline completed successfully!")
            return filtered_cases
            
        except Exception as e:
            self.logger.error(f"Pipeline failed: {e}")
            raise


def main():
    """Main function for command-line usage."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Legal Case Similarity Search Pipeline")
    parser.add_argument("pdf_path", help="Path to the PDF file to analyze")
    parser.add_argument("--case-id", help="Optional case identifier")
    parser.add_argument("--config", default="config.json", help="Path to config file")
    parser.add_argument("--top-k", type=int, help="Number of top similar cases to return (overrides .env)")
    
    args = parser.parse_args()
    
    # Override TOP_K if provided via command line
    if args.top_k:
        os.environ['TOP_K_SIMILAR_CASES'] = str(args.top_k)
    
    # Initialize and run pipeline
    pipeline = SimilarityCaseSearchPipeline(args.config)
    results = pipeline.run_complete_pipeline(args.pdf_path, args.case_id)
    
    return results


if __name__ == "__main__":
    main()