"""
Main Legal Case Processing Pipeline
Orchestrates the complete pipeline from PDF to structured case data.
"""
import os
import sys
import logging
import argparse
import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import asdict
from datetime import datetime

# Add src directory to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '.'))

from convert_pdf_to_md import PDFToMarkdownConverter
from extract_metadata import MetadataExtractor, CaseMetadata
from ontology_matcher import OntologyMatcher, MatchResult
from load_template import TemplateLoader, Template
from extract_facts import FactExtractor
from case_embedder import CaseEmbedder
from dotenv import load_dotenv

load_dotenv()

class LegalCasePipeline:
    """Complete pipeline for processing legal case documents."""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the pipeline with configuration.
        
        Args:
            config (Dict[str, Any]): Configuration dictionary
        """
        self.logger = logging.getLogger(__name__)
        self.config = config
        
        # Initialize pipeline components
        self.pdf_converter = PDFToMarkdownConverter(config)
        self.metadata_extractor = MetadataExtractor(config.get('openai_api_key'))
        self.ontology_matcher = OntologyMatcher(config.get('ontology_path', 'Ontology_schema/ontology_schema.json'))
        self.template_loader = TemplateLoader(config.get('templates_dir', 'templates'))
        self.fact_extractor = FactExtractor(config.get('openai_api_key'))
        
        # Initialize embedder component
        embedding_model = config.get('embedding_model', 'all-mpnet-base-v2')
        embedding_output_dir = config.get('embedding_output_dir', 'Embedding results')
        self.case_embedder = CaseEmbedder(model_name=embedding_model, output_dir=embedding_output_dir)
        
        self.logger.info("Legal case pipeline initialized")
    
    def process_pdf(self, pdf_path: str, output_dir: Optional[str] = None) -> Dict[str, Any]:
        """
        Process a single PDF file through the complete pipeline.
        
        Args:
            pdf_path (str): Path to PDF file
            output_dir (str, optional): Directory for intermediate outputs
            
        Returns:
            ProcessedCase: Complete processed case data
        """
        try:
            self.logger.info(f"Starting pipeline processing for: {pdf_path}")
            
            if not os.path.exists(pdf_path):
                raise FileNotFoundError(f"PDF file not found: {pdf_path}")
            
            # Step 1: Convert PDF to Markdown (in memory)
            self.logger.info("Step 1: Converting PDF to Markdown")
            case_text = self.pdf_converter.extract_text_from_pdf(pdf_path)
            
            # Step 2: Complete extraction using integrated pipeline
            self.logger.info("Step 2: Running complete extraction pipeline")
            extraction_result = self.metadata_extractor.extract_metadata_and_facts(case_text)
            
            if 'error' in extraction_result:
                raise ValueError(f"Extraction failed: {extraction_result['error']}")
            
            # Extract components from result
            extracted_facts = extraction_result['extracted_facts']
            template_used = extraction_result['template_used']
            
            self.logger.info(f"Template used: {extraction_result.get('template_label', template_used)}")
            self.logger.info(f"Extraction confidence: {extraction_result.get('extraction_confidence', 0):.2f}")
            
            # Save only the final extracted facts (no temp files or processed folder)
            case_name = Path(pdf_path).stem
            facts_output_path = f"cases/extracted/{case_name}_facts.json"
            os.makedirs(os.path.dirname(facts_output_path), exist_ok=True)
            
            # Save extracted facts directly (no conversion needed)
            self.fact_extractor.save_extracted_facts(extracted_facts, facts_output_path)
            
            # Step 3: Generate embeddings for the case
            self.logger.info("Step 3: Generating case embeddings")
            try:
                embedding_result = self.case_embedder.embed_case(extracted_facts, case_name)
                self.logger.info(f"Generated embeddings with dimension: {embedding_result['embedding_dimension']}")
            except Exception as e:
                self.logger.warning(f"Embedding generation failed for {case_name}: {e}")
                embedding_result = None
            
            # Create simple result dictionary
            processed_case = {
                'case_id': case_name,
                'template_used': template_used,
                'extraction_confidence': extraction_result.get('extraction_confidence', 0),
                'output_path': facts_output_path,
                'embeddings_generated': embedding_result is not None,
                'embedding_dimension': embedding_result['embedding_dimension'] if embedding_result else None
            }
            
            self.logger.info(f"Pipeline completed successfully for case: {processed_case['case_id']}")
            
            return processed_case
            
        except Exception as e:
            self.logger.error(f"Pipeline processing failed: {e}")
            raise
    
    def process_batch(self, pdf_directory: str, output_base_dir: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Process multiple PDF files in batch.
        
        Args:
            pdf_directory (str): Directory containing PDF files
            output_base_dir (str, optional): Base directory for outputs
            
        Returns:
            List[ProcessedCase]: List of processed cases
        """
        try:
            pdf_files = list(Path(pdf_directory).glob("*.pdf"))
            
            if not pdf_files:
                self.logger.warning(f"No PDF files found in {pdf_directory}")
                return []
            
            self.logger.info(f"Starting batch processing of {len(pdf_files)} files")
            
            processed_cases = []
            failed_files = []
            
            for i, pdf_path in enumerate(pdf_files, 1):
                try:
                    self.logger.info(f"Processing {i}/{len(pdf_files)}: {pdf_path.name}")
                    
                    # Set output directory for this file
                    if output_base_dir:
                        file_output_dir = os.path.join(output_base_dir, pdf_path.stem)
                    else:
                        file_output_dir = None
                    
                    processed_case = self.process_pdf(str(pdf_path), file_output_dir)
                    processed_cases.append(processed_case)
                    
                    self.logger.info(f"Successfully processed: {pdf_path.name}")
                    
                except Exception as e:
                    self.logger.error(f"Failed to process {pdf_path.name}: {e}")
                    failed_files.append(str(pdf_path))
                    
                    # Continue with next file
                    continue
            
            self.logger.info(f"Batch processing completed: {len(processed_cases)} successful, {len(failed_files)} failed")
            
            if failed_files:
                self.logger.warning(f"Failed files: {failed_files}")
            
            # Save all generated embeddings
            if self.case_embedder.case_embeddings:
                self.logger.info("Saving batch embeddings to files...")
                try:
                    saved_files = self.case_embedder.save_embeddings(f"batch_embeddings_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
                    self.logger.info("Batch embeddings saved successfully")
                    
                    # Add embedding info to results
                    embedding_summary = self.case_embedder.get_embedding_summary()
                    for case in processed_cases:
                        case['batch_embedding_files'] = saved_files
                        case['total_embedded_cases'] = embedding_summary['total_cases']
                        
                except Exception as e:
                    self.logger.error(f"Failed to save batch embeddings: {e}")
            
            return processed_cases
            
        except Exception as e:
            self.logger.error(f"Batch processing failed: {e}")
            raise
    
    def get_processing_statistics(self) -> Dict[str, Any]:
        """Get overall processing statistics."""
        return self.case_storage.get_statistics()
    
    def search_processed_cases(self, **criteria) -> List[Dict[str, Any]]:
        """Search processed cases by criteria."""
        return self.case_storage.search_cases(**criteria)
    
    def export_cases(self, output_path: str, case_ids: Optional[List[str]] = None) -> None:
        """Export processed cases to file."""
        self.case_storage.export_cases(output_path, case_ids)
    
    def save_embeddings(self, output_prefix: str = "pipeline_embeddings") -> Dict[str, str]:
        """
        Save all generated embeddings to files.
        
        Args:
            output_prefix (str): Prefix for output files
            
        Returns:
            Dict[str, str]: Paths to saved embedding files
        """
        return self.case_embedder.save_embeddings(output_prefix)
    
    def get_embedding_summary(self) -> Dict[str, Any]:
        """Get summary of generated embeddings."""
        return self.case_embedder.get_embedding_summary()
    
    def embed_existing_cases(self, cases_dir: str = "cases/extracted") -> Dict[str, Any]:
        """
        Generate embeddings for existing case files.
        
        Args:
            cases_dir (str): Directory containing case JSON files
            
        Returns:
            Dict[str, Any]: Summary of embedding generation
        """
        cases_path = Path(cases_dir)
        if not cases_path.exists():
            raise FileNotFoundError(f"Cases directory not found: {cases_dir}")
        
        json_files = list(cases_path.glob("*_facts.json"))
        if not json_files:
            self.logger.warning(f"No case files found in {cases_dir}")
            return {"embedded_cases": 0, "message": "No case files found"}
        
        self.logger.info(f"Generating embeddings for {len(json_files)} existing cases...")
        
        embedded_count = 0
        failed_cases = []
        
        for json_file in json_files:
            try:
                self.case_embedder.embed_case_file(str(json_file))
                embedded_count += 1
                self.logger.debug(f"Embedded case: {json_file.stem}")
            except Exception as e:
                self.logger.error(f"Failed to embed case {json_file.stem}: {e}")
                failed_cases.append(str(json_file))
        
        # Save all embeddings
        if embedded_count > 0:
            saved_files = self.save_embeddings(f"existing_cases_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        else:
            saved_files = {}
        
        embedding_summary = self.get_embedding_summary()
        
        result = {
            "embedded_cases": embedded_count,
            "failed_cases": len(failed_cases),
            "failed_case_files": failed_cases,
            "saved_files": saved_files,
            "embedding_summary": embedding_summary
        }
        
        self.logger.info(f"Embedding generation completed: {embedded_count} successful, {len(failed_cases)} failed")
        return result

def load_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Load pipeline configuration from file or environment.
    
    Args:
        config_path (str, optional): Path to config file
        
    Returns:
        Dict[str, Any]: Configuration dictionary
    """
    config = {
        'openai_api_key': os.getenv('OPENAI_API_KEY'),
        'ontology_path': 'Ontology_schema/ontology_schema.json',
        'templates_dir': 'templates',
        'storage_dir': 'cases/processed',
        'embedding_model': 'all-mpnet-base-v2',  # Using the requested model
        'embedding_output_dir': 'Embedding results'
    }
    
    # Load from config file if provided
    if config_path and os.path.exists(config_path):
        try:
            with open(config_path, 'r') as f:
                file_config = json.load(f)
            config.update(file_config)
        except Exception as e:
            logging.warning(f"Failed to load config file {config_path}: {e}")
    
    return config

def main():
    """Main entry point for the pipeline."""
    parser = argparse.ArgumentParser(description="Legal Case Processing Pipeline")
    parser.add_argument('input', help='PDF file or directory to process')
    parser.add_argument('--config', help='Configuration file path')
    parser.add_argument('--output', help='Output directory for intermediate files')
    parser.add_argument('--batch', action='store_true', help='Process directory in batch mode')
    parser.add_argument('--export', help='Export processed cases to file')
    parser.add_argument('--stats', action='store_true', help='Show processing statistics')
    parser.add_argument('--search', nargs=2, metavar=('KEY', 'VALUE'), 
                       help='Search cases by key-value pair')
    parser.add_argument('--embed-existing', action='store_true', 
                       help='Generate embeddings for existing case files')
    parser.add_argument('--embedding-summary', action='store_true',
                       help='Show embedding summary statistics')
    parser.add_argument('--save-embeddings', metavar='PREFIX',
                       help='Save current embeddings with given prefix')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose logging')
    
    args = parser.parse_args()
    
    # Set up logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    try:
        # Load configuration
        config = load_config(args.config)
        
        # Initialize pipeline
        pipeline = LegalCasePipeline(config)
        
        # Handle different commands
        if args.stats:
            # Show statistics
            stats = pipeline.get_processing_statistics()
            print("Processing Statistics:")
            print(json.dumps(stats, indent=2))
            
        elif args.search:
            # Search cases
            key, value = args.search
            results = pipeline.search_processed_cases(**{key: value})
            print(f"Found {len(results)} matching cases:")
            for case in results:
                print(f"- {case.get('case_id')}: {case.get('case_title', 'No title')}")
        
        elif args.export:
            # Export cases
            pipeline.export_cases(args.export)
            print(f"Cases exported to: {args.export}")
            
        elif args.embed_existing:
            # Generate embeddings for existing cases
            result = pipeline.embed_existing_cases()
            print(f"Embedding generation completed:")
            print(f"- Successfully embedded: {result['embedded_cases']} cases")
            print(f"- Failed: {result['failed_cases']} cases")
            if result['saved_files']:
                print(f"- Saved embedding files:")
                for file_type, path in result['saved_files'].items():
                    print(f"  {file_type}: {path}")
            if result['embedding_summary']:
                print(f"- Total embeddings: {result['embedding_summary']['total_cases']}")
                print(f"- Model used: {result['embedding_summary']['model_name']}")
                print(f"- Embedding dimension: {result['embedding_summary']['embedding_dimension']}")
        
        elif args.embedding_summary:
            # Show embedding summary
            summary = pipeline.get_embedding_summary()
            print("Embedding Summary:")
            print(json.dumps(summary, indent=2))
            
        elif args.save_embeddings:
            # Save embeddings with custom prefix
            try:
                saved_files = pipeline.save_embeddings(args.save_embeddings)
                print(f"Embeddings saved:")
                for file_type, path in saved_files.items():
                    print(f"- {file_type}: {path}")
            except Exception as e:
                print(f"Failed to save embeddings: {e}")
                return 1
        
        elif args.batch:
            # Batch processing
            if not os.path.isdir(args.input):
                print(f"Error: {args.input} is not a directory")
                return 1
            
            processed_cases = pipeline.process_batch(args.input, args.output)
            print(f"Batch processing completed: {len(processed_cases)} cases processed")
            
        else:
            # Single file processing
            if not os.path.isfile(args.input):
                print(f"Error: {args.input} is not a file")
                return 1
            
            processed_case = pipeline.process_pdf(args.input, args.output)
            print(f"Processing completed successfully!")
            print(f"Case ID: {processed_case['case_id']}")
            print(f"Template used: {processed_case['template_used']}")
            print(f"Extraction confidence: {processed_case['extraction_confidence']:.2f}")
            print(f"Output saved to: {processed_case['output_path']}")
        
        return 0
        
    except Exception as e:
        logging.error(f"Pipeline execution failed: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())