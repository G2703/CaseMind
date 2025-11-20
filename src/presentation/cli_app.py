"""
CLI application for CaseMind legal similarity search.
Main entry point for user interaction.
"""

import asyncio
import logging
from pathlib import Path
from typing import Optional

from rich.prompt import Prompt, Confirm
from rich import print as rprint

from presentation.formatters import RichFormatter, console
from pipelines.ingestion_pipeline import DataIngestionPipeline
from pipelines.similarity_pipeline import SimilaritySearchPipeline
from infrastructure.document_store import PGVectorDocumentStore
from core.config import Config
from core.exceptions import CaseMindException

logger = logging.getLogger(__name__)


class CLIApp:
    """Main CLI application controller."""
    
    def __init__(self):
        """Initialize CLI application."""
        self.config = Config()
        self.formatter = RichFormatter()
        self.ingestion_pipeline: Optional[DataIngestionPipeline] = None
        self.similarity_pipeline: Optional[SimilaritySearchPipeline] = None
        self.store: Optional[PGVectorDocumentStore] = None
        self.running = False
        
        logger.info("CLI Application initialized")
    
    async def start(self):
        """Start the CLI application."""
        self.formatter.display_welcome()
        
        # Initialize backend
        if not await self._initialize_backend():
            self.formatter.print_error("Failed to initialize backend. Exiting.")
            return
        
        self.running = True
        
        # Main menu loop
        while self.running:
            try:
                self.formatter.display_menu()
                choice = Prompt.ask("Select an option", choices=["1", "2", "3", "4", "5"])
                
                if choice == "1":
                    await self._ingest_cases_batch()
                elif choice == "2":
                    await self._find_similar_cases()
                elif choice == "3":
                    await self._show_statistics()
                elif choice == "4":
                    await self._health_check()
                elif choice == "5":
                    await self._shutdown()
                
            except KeyboardInterrupt:
                rprint("\n")
                if Confirm.ask("Do you want to exit?"):
                    await self._shutdown()
            except Exception as e:
                logger.error(f"Error in main loop: {e}")
                self.formatter.print_error(f"An error occurred: {str(e)}")
    
    async def _initialize_backend(self) -> bool:
        """
        Initialize backend services.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            console.print("\n[bold cyan]Initializing backend services...[/bold cyan]")
            
            # Initialize pipelines (reuse ingestion_pipeline to avoid duplicate TemplateSelector)
            self.ingestion_pipeline = DataIngestionPipeline()
            self.similarity_pipeline = SimilaritySearchPipeline(ingestion_pipeline=self.ingestion_pipeline)
            self.store = PGVectorDocumentStore()
            
            # Check database connection
            console.print("  • Testing database connection...")
            stats = self.store.get_statistics()
            
            self.formatter.print_success("Backend initialized successfully")
            self.formatter.print_info(f"Database: {stats.get('total_documents', 0)} cases indexed")
            
            return True
            
        except Exception as e:
            logger.error(f"Backend initialization failed: {e}")
            self.formatter.print_error(f"Backend initialization failed: {str(e)}")
            return False
    
    async def _ingest_cases_batch(self):
        """Ingest cases from a folder (batch processing)."""
        console.print("\n[bold cyan]═══ Batch Case Ingestion ═══[/bold cyan]\n")
        
        # Get folder path
        folder_path = Prompt.ask("Enter folder path containing PDF files")
        folder_path = Path(folder_path)
        
        if not folder_path.exists():
            self.formatter.print_error(f"Folder not found: {folder_path}")
            return
        
        # Count PDF files
        pdf_files = list(folder_path.glob("*.pdf"))
        if not pdf_files:
            self.formatter.print_warning("No PDF files found in folder")
            return
        
        self.formatter.print_info(f"Found {len(pdf_files)} PDF files")
        
        # Confirm
        if not Confirm.ask(f"Proceed with batch ingestion of {len(pdf_files)} files?"):
            self.formatter.print_info("Batch ingestion cancelled")
            return
        
        # Process batch
        try:
            with self.formatter.display_progress_bar(len(pdf_files), "Ingesting cases") as progress:
                task = progress.add_task("Processing...", total=len(pdf_files))
                
                # Run batch ingestion (this will update progress internally)
                result = await self.ingestion_pipeline.process_batch(folder_path)
                
                progress.update(task, completed=len(pdf_files))
            
            # Display results
            console.print()
            console.print(self.formatter.format_batch_result(result))
            
            if result.case_ids:
                self.formatter.print_success(f"Successfully ingested {len(result.case_ids)} cases")
            
        except Exception as e:
            logger.error(f"Batch ingestion error: {e}")
            self.formatter.print_error(f"Batch ingestion failed: {str(e)}")
    
    async def _find_similar_cases(self):
        """Find similar cases for a query case."""
        console.print("\n[bold cyan]═══ Find Similar Cases ═══[/bold cyan]\n")
        
        # Get file path
        file_path = Prompt.ask("Enter path to query PDF file")
        file_path = Path(file_path)
        
        if not file_path.exists():
            self.formatter.print_error(f"File not found: {file_path}")
            return
        
        # Search mode
        console.print("\n[bold cyan]Search Mode:[/bold cyan]")
        console.print("  1. Search by Case Facts (default)")
        console.print("  2. Search by Case Metadata (case name, court, sections)")
        
        search_mode = Prompt.ask("Select search mode", choices=["1", "2"], default="1")
        use_metadata = (search_mode == "2")
        
        # Run similarity search
        try:
            console.print("\n[bold cyan]Processing query case...[/bold cyan]")
            
            with console.status("[bold green]Running similarity pipeline...") as status:
                result = await self.similarity_pipeline.run_full_pipeline(
                    file_path,
                    use_metadata_query=use_metadata
                )
            
            # Display query case info
            console.print("\n")
            console.print(self.formatter.format_metadata(result.input_case.metadata))
            console.print()
            console.print(self.formatter.format_facts_summary(result.input_case.facts_summary))
            
            # Display similar cases
            console.print("\n")
            if result.total_above_threshold > 0:
                console.print(self.formatter.format_similar_cases(result.similar_cases))
                self.formatter.print_success(f"Found {result.total_above_threshold} similar cases")
            else:
                self.formatter.print_warning("No similar cases found")
            
        except Exception as e:
            logger.error(f"Similarity search error: {e}")
            self.formatter.print_error(f"Similarity search failed: {str(e)}")
    
    async def _show_statistics(self):
        """Display database statistics."""
        console.print("\n[bold cyan]═══ Database Statistics ═══[/bold cyan]\n")
        
        try:
            stats = self.store.get_statistics()
            console.print(self.formatter.format_statistics(stats))
            
        except Exception as e:
            logger.error(f"Statistics retrieval error: {e}")
            self.formatter.print_error(f"Failed to retrieve statistics: {str(e)}")
    
    async def _health_check(self):
        """Perform health check on all components."""
        console.print("\n[bold cyan]═══ System Health Check ═══[/bold cyan]\n")
        
        health_status = {}
        
        # Check database
        try:
            self.store.get_statistics()
            health_status["PostgreSQL Database"] = True
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            health_status["PostgreSQL Database"] = False
        
        # Check pgvector
        try:
            self.store.ensure_pgvector_extension()
            health_status["pgvector Extension"] = True
        except Exception as e:
            logger.error(f"pgvector health check failed: {e}")
            health_status["pgvector Extension"] = False
        
        # Check embedding service
        try:
            test_embedding = self.similarity_pipeline.embedder.embed_query("test")
            health_status["Embedding Service"] = len(test_embedding) == 768
        except Exception as e:
            logger.error(f"Embedding service health check failed: {e}")
            health_status["Embedding Service"] = False
        
        # Check cross-encoder
        try:
            self.similarity_pipeline.cross_encoder.predict([("test", "test")])
            health_status["Cross-Encoder"] = True
        except Exception as e:
            logger.error(f"Cross-encoder health check failed: {e}")
            health_status["Cross-Encoder"] = False
        
        # Check OpenAI API (if configured)
        openai_key = self.config.get("OPENAI_API_KEY")
        if openai_key and openai_key != "your_key_here":
            health_status["OpenAI API"] = True
        else:
            health_status["OpenAI API"] = False
        
        # Display results
        self.formatter.display_health_status(health_status)
    
    async def _shutdown(self):
        """Shutdown the application."""
        console.print("\n[bold cyan]Shutting down CaseMind...[/bold cyan]")
        
        # Close database connections
        if self.store:
            try:
                # Close connection (if connection pooling is implemented)
                pass
            except Exception as e:
                logger.error(f"Error closing database connection: {e}")
        
        self.formatter.print_success("Goodbye!")
        self.running = False


async def main():
    """Main entry point for CLI application."""
    app = CLIApp()
    await app.start()


if __name__ == "__main__":
    asyncio.run(main())
