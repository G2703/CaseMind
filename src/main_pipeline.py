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

# Add src directory to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '.'))

from convert_pdf_to_md import PDFToMarkdownConverter
from extract_metadata import MetadataExtractor, CaseMetadata
from ontology_matcher import OntologyMatcher, MatchResult
from load_template import TemplateLoader, Template
from extract_facts import FactExtractor, ExtractedFacts
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
        self.ontology_matcher = OntologyMatcher(config.get('ontology_path', 'ontology_schema.json'))
        self.template_loader = TemplateLoader(config.get('templates_dir', 'templates'))
        self.fact_extractor = FactExtractor(config.get('openai_api_key'))
        
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
            
            # Convert dict back to ExtractedFacts object for saving
            from extract_facts import ExtractedFacts
            extracted_facts_obj = ExtractedFacts(**extracted_facts)
            self.fact_extractor.save_extracted_facts(extracted_facts_obj, facts_output_path)
            
            # Create simple result dictionary
            processed_case = {
                'case_id': case_name,
                'template_used': template_used,
                'extraction_confidence': extraction_result.get('extraction_confidence', 0),
                'output_path': facts_output_path
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
        'ontology_path': 'ontology_schema.json',
        'templates_dir': 'templates',
        'storage_dir': 'cases/processed'
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