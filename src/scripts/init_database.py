"""
Database initialization script.
Creates schema, enables pgvector, and validates setup.
"""

import sys
import logging
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.infrastructure.document_store import PGVectorDocumentStore
from src.core.config import Config
from rich.console import Console
from rich.panel import Panel

console = Console()
logger = logging.getLogger(__name__)


def check_connection() -> bool:
    """
    Check database connection.
    
    Returns:
        True if connection successful, False otherwise
    """
    try:
        console.print("[bold cyan]Checking database connection...[/bold cyan]")
        store = PGVectorDocumentStore()
        
        # Try a simple query
        store.get_statistics()
        
        console.print("[bold green]✓[/bold green] Database connection successful")
        return True
        
    except Exception as e:
        console.print(f"[bold red]✗[/bold red] Database connection failed: {str(e)}")
        return False


def ensure_pgvector() -> bool:
    """
    Ensure pgvector extension is installed.
    
    Returns:
        True if successful, False otherwise
    """
    try:
        console.print("[bold cyan]Checking pgvector extension...[/bold cyan]")
        store = PGVectorDocumentStore()
        store.ensure_pgvector_extension()
        
        console.print("[bold green]✓[/bold green] pgvector extension enabled")
        return True
        
    except Exception as e:
        console.print(f"[bold red]✗[/bold red] pgvector setup failed: {str(e)}")
        console.print("\n[bold yellow]Make sure pgvector is installed on your PostgreSQL server.[/bold yellow]")
        console.print("See README_HAYSTACK.md for installation instructions.")
        return False


def create_schema() -> bool:
    """
    Create database schema.
    
    Returns:
        True if successful, False otherwise
    """
    try:
        console.print("[bold cyan]Creating database schema...[/bold cyan]")
        store = PGVectorDocumentStore()
        store.create_schema()
        
        console.print("[bold green]✓[/bold green] Database schema created")
        return True
        
    except Exception as e:
        console.print(f"[bold red]✗[/bold red] Schema creation failed: {str(e)}")
        return False


def verify_setup() -> bool:
    """
    Verify database setup.
    
    Returns:
        True if verification successful, False otherwise
    """
    try:
        console.print("[bold cyan]Verifying database setup...[/bold cyan]")
        store = PGVectorDocumentStore()
        
        # Get statistics
        stats = store.get_statistics()
        
        console.print(f"[bold green]✓[/bold green] Database verified")
        console.print(f"  • Total cases: {stats.get('total_cases', 0)}")
        console.print(f"  • Database size: {stats.get('database_size', 'N/A')}")
        
        return True
        
    except Exception as e:
        console.print(f"[bold red]✗[/bold red] Verification failed: {str(e)}")
        return False


def main():
    """Main initialization routine."""
    console.print("\n")
    console.print(Panel.fit(
        "[bold blue]CaseMind Database Initialization[/bold blue]",
        border_style="blue"
    ))
    console.print("\n")
    
    # Load configuration
    config = Config()
    
    console.print(f"[bold cyan]Configuration:[/bold cyan]")
    console.print(f"  • Host: {config.get('POSTGRES_HOST')}")
    console.print(f"  • Port: {config.get('POSTGRES_PORT')}")
    console.print(f"  • Database: {config.get('POSTGRES_DB')}")
    console.print("\n")
    
    # Step 1: Check connection
    if not check_connection():
        console.print("\n[bold red]Initialization failed at connection check.[/bold red]")
        console.print("Please check your PostgreSQL configuration in .env file.")
        return False
    
    # Step 2: Ensure pgvector
    if not ensure_pgvector():
        console.print("\n[bold red]Initialization failed at pgvector setup.[/bold red]")
        return False
    
    # Step 3: Create schema
    if not create_schema():
        console.print("\n[bold red]Initialization failed at schema creation.[/bold red]")
        return False
    
    # Step 4: Verify setup
    if not verify_setup():
        console.print("\n[bold red]Initialization failed at verification.[/bold red]")
        return False
    
    # Success
    console.print("\n")
    console.print(Panel.fit(
        "[bold green]✓ Database initialization completed successfully![/bold green]",
        border_style="green"
    ))
    console.print("\n")
    
    return True


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    success = main()
    sys.exit(0 if success else 1)
