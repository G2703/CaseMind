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
from rich.panel import Panel

from presentation.formatters import RichFormatter, console
from pipelines import HaystackIngestionPipeline, PureHaystackSimilarityPipeline
from core.config import Config
from core.exceptions import CaseMindException

logger = logging.getLogger(__name__)


class CLIApp:
    """Main CLI application controller."""
    
    def __init__(self):
        """Initialize CLI application."""
        self.config = Config()
        self.formatter = RichFormatter()
        self.ingestion_pipeline: Optional[HaystackIngestionPipeline] = None
        self.similarity_pipeline: Optional[PureHaystackSimilarityPipeline] = None
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
            
            # Initialize pure Haystack pipelines
            console.print("  • Loading ingestion pipeline...")
            self.ingestion_pipeline = HaystackIngestionPipeline()
            
            console.print("  • Loading similarity pipeline...")
            self.similarity_pipeline = PureHaystackSimilarityPipeline()
            
            # Check database connection and count legal_cases
            console.print("  • Testing database connection...")
            doc_count = self.ingestion_pipeline.count_legal_cases()
            
            self.formatter.print_success("Backend initialized successfully")
            self.formatter.print_info(f"Database: {doc_count} cases indexed")
            
            return True
            
        except Exception as e:
            import traceback
            logger.error(f"Backend initialization failed: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")
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
            completed = 0
            skipped = 0
            failed = 0
            
            with self.formatter.display_progress_bar(len(pdf_files), "Ingesting cases") as progress:
                task = progress.add_task("Processing...", total=len(pdf_files))
                
                for pdf_file in pdf_files:
                    try:
                        result = await self.ingestion_pipeline.ingest_single(pdf_file, display_summary=False)
                        if result.status.value == "completed":
                            completed += 1
                        elif result.status.value == "skipped_duplicate":
                            skipped += 1
                        else:
                            failed += 1
                    except Exception as e:
                        logger.error(f"Failed to ingest {pdf_file.name}: {e}")
                        failed += 1
                    
                    progress.update(task, advance=1)
            
            # Display results
            console.print()
            self.formatter.print_success(f"Batch ingestion complete")
            console.print(f"  • Completed: {completed}")
            console.print(f"  • Skipped (duplicates): {skipped}")
            console.print(f"  • Failed: {failed}")
            
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
        
        # Run similarity search (always uses case facts with hybrid scoring)
        try:
            console.print("\n[bold cyan]Processing query case...[/bold cyan]")
            
            with console.status("[bold green]Running similarity pipeline...") as status:
                result = await self.similarity_pipeline.search_similar(file_path)
            
            # Display query case info
            console.print("\n")
            console.print(Panel.fit(
                "[bold cyan]Query Case Information[/bold cyan]",
                border_style="cyan"
            ))
            console.print()
            
            if result.input_case and result.input_case.metadata:
                # Display metadata
                console.print(self.formatter.format_metadata(result.input_case.metadata))
                console.print()
                
                # Display facts summary if available
                if result.input_case.facts_summary and len(result.input_case.facts_summary.strip()) > 0:
                    console.print(self.formatter.format_facts_summary(result.input_case.facts_summary))
                    console.print()
                else:
                    console.print(Panel(
                        "[yellow]No facts summary available (OpenAI API key required for fact extraction)[/yellow]",
                        title="⚠️ Note",
                        border_style="yellow"
                    ))
                    console.print()
            
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
            # Get statistics from legal_cases table
            stats = self.ingestion_pipeline.get_legal_cases_statistics()
            
            # Add additional metadata
            stats["database"] = "PostgreSQL + pgvector"
            stats["embedding_model"] = "sentence-transformers/all-mpnet-base-v2"
            stats["ranker_model"] = "cross-encoder/ms-marco-MiniLM-L-6-v2"
            
            console.print(self.formatter.format_statistics(stats))
            
        except Exception as e:
            logger.error(f"Statistics retrieval error: {e}")
            self.formatter.print_error(f"Failed to retrieve statistics: {str(e)}")
    
    async def _health_check(self):
        """Perform health check on all components."""
        console.print("\n[bold cyan]═══ System Health Check ═══[/bold cyan]\n")
        
        health_status = {}
        
        # Check database connection and legal_cases table
        try:
            case_count = self.ingestion_pipeline.count_legal_cases()
            health_status["PostgreSQL Database"] = True
            health_status["legal_cases Table"] = True
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            health_status["PostgreSQL Database"] = False
            health_status["legal_cases Table"] = False
        
        # Check pgvector extension
        try:
            # If document store works, pgvector is working
            self.similarity_pipeline.document_store.count_documents()
            health_status["pgvector Extension"] = True
        except Exception as e:
            logger.error(f"pgvector health check failed: {e}")
            health_status["pgvector Extension"] = False
        
        # Check Haystack pipelines
        try:
            health_status["Ingestion Pipeline"] = self.ingestion_pipeline is not None
            health_status["Similarity Pipeline"] = self.similarity_pipeline is not None
        except Exception as e:
            logger.error(f"Pipeline health check failed: {e}")
            health_status["Ingestion Pipeline"] = False
            health_status["Similarity Pipeline"] = False
        
        # Check OpenAI API (if configured)
        openai_key = self.config.get("OPENAI_API_KEY", "")
        if openai_key and openai_key != "your_key_here" and openai_key != "":
            health_status["OpenAI API"] = True
        else:
            health_status["OpenAI API"] = False
        
        # Display results
        self.formatter.display_health_status(health_status)
    
    async def _shutdown(self):
        """Shutdown the application."""
        console.print("\n[bold cyan]Shutting down CaseMind...[/bold cyan]")
        
        # Cleanup (Haystack handles connections internally)
        logger.info("Cleaning up resources...")
        
        self.formatter.print_success("Goodbye!")
        self.running = False


async def main():
    """Main entry point for CLI application."""
    app = CLIApp()
    await app.start()


if __name__ == "__main__":
    asyncio.run(main())
