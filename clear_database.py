"""
Script to clear all documents from the database.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from src.core.config import Config
import psycopg2

def clear_database():
    """Clear all documents from haystack_documents table."""
    config = Config()
    
    conn_str = f"postgresql://{config.db_user}:{config.db_password}@{config.db_host}:{config.db_port}/{config.db_name}"
    
    try:
        conn = psycopg2.connect(conn_str)
        cursor = conn.cursor()
        
        # Count before deletion
        cursor.execute('SELECT COUNT(*) FROM haystack_documents')
        count_before = cursor.fetchone()[0]
        print(f"Documents before deletion: {count_before}")
        
        # Delete all documents
        cursor.execute('DELETE FROM haystack_documents')
        conn.commit()
        
        # Count after deletion
        cursor.execute('SELECT COUNT(*) FROM haystack_documents')
        count_after = cursor.fetchone()[0]
        print(f"Documents after deletion: {count_after}")
        
        cursor.close()
        conn.close()
        
        print("\n✓ All documents cleared successfully!")
        print(f"  Removed {count_before} documents from the database.")
        
    except Exception as e:
        print(f"✗ Error clearing database: {e}")
        sys.exit(1)

if __name__ == "__main__":
    clear_database()
