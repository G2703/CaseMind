"""
Database initialization script for pure Haystack architecture.
Creates schema, enables pgvector, and validates setup.
"""

import sys
import logging
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.core.config import Config
from haystack_integrations.document_stores.pgvector import PgvectorDocumentStore
from haystack.utils import Secret
from rich.console import Console
from rich.panel import Panel
import psycopg2

console = Console()
logger = logging.getLogger(__name__)


def get_connection_string(config: Config) -> str:
    """Build PostgreSQL connection string."""
    return f"postgresql://{config.db_user}:{config.db_password}@{config.db_host}:{config.db_port}/{config.db_name}"


def check_connection(config: Config) -> bool:
    """
    Check database connection.
    
    Returns:
        True if connection successful, False otherwise
    """
    try:
        console.print("[bold cyan]Checking database connection...[/bold cyan]")
        
        conn_str = get_connection_string(config)
        conn = psycopg2.connect(conn_str)
        conn.close()
        
        console.print("[bold green]✓[/bold green] Database connection successful")
        return True
        
    except Exception as e:
        console.print(f"[bold red]✗[/bold red] Database connection failed: {str(e)}")
        return False


def ensure_pgvector(config: Config) -> bool:
    """
    Ensure pgvector extension is installed.
    
    Returns:
        True if successful, False otherwise
    """
    try:
        console.print("[bold cyan]Checking pgvector extension...[/bold cyan]")
        
        conn_str = get_connection_string(config)
        conn = psycopg2.connect(conn_str)
        cursor = conn.cursor()
        
        # Enable pgvector extension
        cursor.execute("CREATE EXTENSION IF NOT EXISTS vector;")
        conn.commit()
        
        cursor.close()
        conn.close()
        
        console.print("[bold green]✓[/bold green] pgvector extension enabled")
        return True
        
    except Exception as e:
        console.print(f"[bold red]✗[/bold red] pgvector setup failed: {str(e)}")
        console.print("\n[bold yellow]Make sure pgvector is installed on your PostgreSQL server.[/bold yellow]")
        console.print("Installation: https://github.com/pgvector/pgvector#installation")
        return False


def create_schema(config: Config) -> bool:
    """
    Create database schema using Haystack's PgvectorDocumentStore.
    
    Returns:
        True if successful, False otherwise
    """
    try:
        console.print("[bold cyan]Creating database schema...[/bold cyan]")
        
        conn_str = get_connection_string(config)
        
        # Initialize document store (this creates the table)
        store = PgvectorDocumentStore(
            connection_string=Secret.from_token(conn_str),
            table_name="haystack_documents",
            embedding_dimension=768,
            vector_function="cosine_similarity",
            recreate_table=False,  # Don't recreate if exists
            search_strategy="hnsw",
            hnsw_recreate_index_if_exists=False,
            hnsw_index_creation_kwargs={
                "m": 16,
                "ef_construction": 64
            }
        )
        
        console.print("[bold green]✓[/bold green] Database schema created")
        return True
        
    except Exception as e:
        console.print(f"[bold red]✗[/bold red] Schema creation failed: {str(e)}")
        return False


def verify_setup(config: Config) -> bool:
    """
    Verify database setup.
    
    Returns:
        True if verification successful, False otherwise
    """
    try:
        console.print("[bold cyan]Verifying database setup...[/bold cyan]")
        
        conn_str = get_connection_string(config)
        store = PgvectorDocumentStore(
            connection_string=Secret.from_token(conn_str),
            table_name="haystack_documents",
            embedding_dimension=768,
            vector_function="cosine_similarity",
            recreate_table=False
        )
        
        # Count documents
        doc_count = store.count_documents()
        
        console.print(f"[bold green]✓[/bold green] Database verified")
        console.print(f"  • Total documents: {doc_count}")
        console.print(f"  • Table: haystack_documents")
        console.print(f"  • Embedding dimension: 768")
        
        return True
        
    except Exception as e:
        console.print(f"[bold red]✗[/bold red] Verification failed: {str(e)}")
        return False


def main():
    """Main initialization routine."""
    console.print("\n")
    console.print(Panel.fit(
        "[bold blue]CaseMind Database Initialization[/bold blue]\n[dim]Pure Haystack Architecture[/dim]",
        border_style="blue"
    ))
    console.print("\n")
    
    # Load configuration
    config = Config()
    
    console.print(f"[bold cyan]Configuration:[/bold cyan]")
    console.print(f"  • Host: {config.db_host}")
    console.print(f"  • Port: {config.db_port}")
    console.print(f"  • Database: {config.db_name}")
    console.print(f"  • User: {config.db_user}")
    console.print("\n")
    
    # Step 1: Check connection
    if not check_connection(config):
        console.print("\n[bold red]Initialization failed at connection check.[/bold red]")
        console.print("Please check your PostgreSQL configuration in .env file.")
        return False
    
    # Step 2: Ensure pgvector
    if not ensure_pgvector(config):
        console.print("\n[bold red]Initialization failed at pgvector setup.[/bold red]")
        return False
    
    # Step 3: Create schema
    if not create_schema(config):
        console.print("\n[bold red]Initialization failed at schema creation.[/bold red]")
        return False
    
    # Step 4: Verify setup
    if not verify_setup(config):
        console.print("\n[bold red]Initialization failed at verification.[/bold red]")
        return False
    
    # Success
    console.print("\n")
    console.print(Panel.fit(
        "[bold green]✓ Database initialization completed successfully![/bold green]\n\n"
        "[dim]You can now run:[/dim]\n"
        "[bold cyan]python src/main.py[/bold cyan]",
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
