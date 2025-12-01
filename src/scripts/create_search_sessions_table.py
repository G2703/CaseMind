"""
Create search_sessions table for web app temporary search queries.
This table tracks user search sessions without polluting the legal_cases database.
"""

import sys
import logging
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.core.config import Config
import psycopg2
from rich.console import Console
from rich.panel import Panel

console = Console()
logger = logging.getLogger(__name__)


def get_connection_string(config: Config) -> str:
    """Build PostgreSQL connection string."""
    return f"postgresql://{config.db_user}:{config.db_password}@{config.db_host}:{config.db_port}/{config.db_name}"


def create_search_sessions_table(config: Config) -> bool:
    """
    Create search_sessions table with all required columns and indexes.
    
    Returns:
        True if successful, False otherwise
    """
    try:
        console.print("[bold cyan]Creating search_sessions table...[/bold cyan]")
        
        conn_str = get_connection_string(config)
        conn = psycopg2.connect(conn_str)
        cursor = conn.cursor()
        
        # Create search_sessions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS search_sessions (
                -- Primary identifier
                session_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                
                -- File information
                uploaded_filename VARCHAR NOT NULL,
                file_size_bytes INTEGER,
                file_hash VARCHAR,
                
                -- Processing status
                status VARCHAR(20) NOT NULL DEFAULT 'uploaded',
                current_phase VARCHAR(50),
                current_step VARCHAR(100),
                progress_percentage INTEGER DEFAULT 0,
                
                -- Temporary storage paths
                pdf_temp_path VARCHAR,
                markdown_temp_path VARCHAR,
                
                -- Processing results (temporary, in-memory)
                summary JSONB,
                factual_summary JSONB,
                embeddings JSONB,
                
                -- Search results (cached)
                similar_cases JSONB,
                search_params JSONB,
                
                -- Error tracking
                error_message TEXT,
                error_phase VARCHAR(50),
                error_stack TEXT,
                
                -- Timestamps
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                pdf_extracted_at TIMESTAMP WITH TIME ZONE,
                summarization_completed_at TIMESTAMP WITH TIME ZONE,
                facts_extracted_at TIMESTAMP WITH TIME ZONE,
                search_completed_at TIMESTAMP WITH TIME ZONE,
                expires_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP + INTERVAL '24 hours',
                
                -- Flags
                is_duplicate BOOLEAN DEFAULT FALSE,
                duplicate_of_file_id VARCHAR
            );
        """)
        
        console.print("  • Table structure created")
        
        # Create indexes
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_search_sessions_status 
            ON search_sessions(status);
        """)
        console.print("  • Index on status created")
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_search_sessions_created 
            ON search_sessions(created_at DESC);
        """)
        console.print("  • Index on created_at created")
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_search_sessions_expires 
            ON search_sessions(expires_at);
        """)
        console.print("  • Index on expires_at created")
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_search_sessions_file_hash 
            ON search_sessions(file_hash);
        """)
        console.print("  • Index on file_hash created")
        
        # Create auto-update trigger for updated_at
        cursor.execute("""
            CREATE OR REPLACE FUNCTION update_search_sessions_timestamp()
            RETURNS TRIGGER AS $$
            BEGIN
                NEW.updated_at = CURRENT_TIMESTAMP;
                RETURN NEW;
            END;
            $$ LANGUAGE plpgsql;
        """)
        console.print("  • Timestamp update function created")
        
        cursor.execute("""
            DROP TRIGGER IF EXISTS search_sessions_timestamp_trigger ON search_sessions;
            
            CREATE TRIGGER search_sessions_timestamp_trigger
                BEFORE UPDATE ON search_sessions
                FOR EACH ROW
                EXECUTE FUNCTION update_search_sessions_timestamp();
        """)
        console.print("  • Auto-update trigger created")
        
        conn.commit()
        cursor.close()
        conn.close()
        
        console.print("[bold green]✓[/bold green] search_sessions table created successfully")
        return True
        
    except Exception as e:
        console.print(f"[bold red]✗[/bold red] Failed to create search_sessions table: {str(e)}")
        logger.error(f"Table creation failed: {e}")
        return False


def verify_table(config: Config) -> bool:
    """
    Verify search_sessions table structure.
    
    Returns:
        True if verification successful, False otherwise
    """
    try:
        console.print("\n[bold cyan]Verifying search_sessions table...[/bold cyan]")
        
        conn_str = get_connection_string(config)
        conn = psycopg2.connect(conn_str)
        cursor = conn.cursor()
        
        # Check if table exists
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'search_sessions'
            );
        """)
        
        exists = cursor.fetchone()[0]
        
        if not exists:
            console.print("[bold red]✗[/bold red] search_sessions table does not exist")
            return False
        
        console.print("  • Table exists")
        
        # Count columns
        cursor.execute("""
            SELECT COUNT(*) 
            FROM information_schema.columns 
            WHERE table_name = 'search_sessions';
        """)
        
        column_count = cursor.fetchone()[0]
        console.print(f"  • Columns: {column_count}")
        
        # Count indexes
        cursor.execute("""
            SELECT COUNT(*) 
            FROM pg_indexes 
            WHERE tablename = 'search_sessions';
        """)
        
        index_count = cursor.fetchone()[0]
        console.print(f"  • Indexes: {index_count}")
        
        # Check trigger exists
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM pg_trigger 
                WHERE tgname = 'search_sessions_timestamp_trigger'
            );
        """)
        
        trigger_exists = cursor.fetchone()[0]
        console.print(f"  • Auto-update trigger: {'✓' if trigger_exists else '✗'}")
        
        cursor.close()
        conn.close()
        
        console.print("[bold green]✓[/bold green] Table verification successful")
        return True
        
    except Exception as e:
        console.print(f"[bold red]✗[/bold red] Verification failed: {str(e)}")
        return False


def main():
    """Main execution routine."""
    console.print("\n")
    console.print(Panel.fit(
        "[bold blue]CaseMind Web App - Database Setup[/bold blue]\n"
        "[dim]Creating search_sessions table for temporary search queries[/dim]",
        border_style="blue"
    ))
    console.print("\n")
    
    # Load configuration
    config = Config()
    
    console.print(f"[bold cyan]Database Configuration:[/bold cyan]")
    console.print(f"  • Host: {config.db_host}")
    console.print(f"  • Port: {config.db_port}")
    console.print(f"  • Database: {config.db_name}")
    console.print(f"  • User: {config.db_user}")
    console.print("\n")
    
    # Create table
    if not create_search_sessions_table(config):
        console.print("\n[bold red]Setup failed.[/bold red]")
        return False
    
    # Verify table
    if not verify_table(config):
        console.print("\n[bold red]Verification failed.[/bold red]")
        return False
    
    console.print("\n[bold green]✓ Setup completed successfully![/bold green]")
    console.print("\n[dim]The search_sessions table is ready for the web application.[/dim]")
    console.print("[dim]This table will store temporary search queries without polluting legal_cases.[/dim]\n")
    
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
