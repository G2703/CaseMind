"""
Initialize Weaviate collections for CaseMind.
Creates all 4 collections with proper schemas if they don't exist.
"""

import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from src.core.config import Config
from src.infrastructure.weaviate_client import WeaviateClient
from src.infrastructure.weaviate_schema import (
    CASE_DOCUMENTS_SCHEMA,
    CASE_METADATA_SCHEMA,
    CASE_SECTIONS_SCHEMA,
    CASE_CHUNKS_SCHEMA
)
from src.utils.logger import get_logger

logger = get_logger(__name__)


def init_weaviate(force_recreate: bool = False):
    """
    Initialize Weaviate with all required collections.
    
    Args:
        force_recreate: If True, delete and recreate existing collections
    """
    config = Config()
    client_wrapper = WeaviateClient()
    client = client_wrapper.client
    
    logger.info("Initializing Weaviate collections...")
    
    # Check if Weaviate is ready
    if not client_wrapper.is_ready():
        logger.error("Weaviate is not ready. Please check your Weaviate instance.")
        return False
    
    # Collection schemas to create
    schemas = [
        ("CaseDocuments", CASE_DOCUMENTS_SCHEMA),
        ("CaseMetadata", CASE_METADATA_SCHEMA),
        ("CaseSections", CASE_SECTIONS_SCHEMA),
        ("CaseChunks", CASE_CHUNKS_SCHEMA)
    ]
    
    created_count = 0
    skipped_count = 0
    
    for collection_name, schema in schemas:
        try:
            # Check if collection exists
            if client.collections.exists(collection_name):
                if force_recreate:
                    logger.warning(f"Deleting existing collection: {collection_name}")
                    client.collections.delete(collection_name)
                else:
                    logger.info(f"Collection already exists (skipping): {collection_name}")
                    skipped_count += 1
                    continue
            
            # Create collection
            logger.info(f"Creating collection: {collection_name}")
            client.collections.create_from_dict(schema)
            created_count += 1
            logger.info(f"✓ Created: {collection_name}")
            
        except Exception as e:
            logger.error(f"Failed to create {collection_name}: {str(e)}", exc_info=True)
            return False
    
    # Verify all collections
    logger.info("\nVerifying collections...")
    all_collections = client.collections.list_all()
    
    required_collections = {"CaseDocuments", "CaseMetadata", "CaseSections", "CaseChunks"}
    existing_collections = set(all_collections.keys())
    
    missing = required_collections - existing_collections
    
    if missing:
        logger.error(f"Missing collections: {missing}")
        return False
    
    # Print collection details
    logger.info("\nCollection Summary:")
    logger.info("=" * 60)
    
    for name in required_collections:
        collection = client.collections.get(name)
        config_data = collection.config.get()
        
        # Count objects
        result = collection.aggregate.over_all()
        count = result.total_count
        
        # Vector config
        vector_config = "No vectors"
        if config_data.vector_config:
            vector_config = f"Vector: {config_data.vector_config}"
        
        logger.info(f"{name}:")
        logger.info(f"  Objects: {count}")
        logger.info(f"  {vector_config}")
        logger.info("")
    
    logger.info("=" * 60)
    logger.info(f"Initialization complete: {created_count} created, {skipped_count} skipped")
    
    client_wrapper.close()
    return True


def delete_all_collections():
    """Delete all CaseMind collections (use with caution!)."""
    config = Config()
    client_wrapper = WeaviateClient()
    client = client_wrapper.client
    
    collection_names = ["CaseDocuments", "CaseMetadata", "CaseSections", "CaseChunks"]
    
    logger.warning("⚠️  Deleting all collections...")
    
    for name in collection_names:
        if client.collections.exists(name):
            logger.info(f"Deleting: {name}")
            client.collections.delete(name)
    
    logger.info("All collections deleted")
    client_wrapper.close()


def get_collection_stats():
    """Get statistics for all collections."""
    config = Config()
    client_wrapper = WeaviateClient()
    client = client_wrapper.client
    
    collection_names = ["CaseDocuments", "CaseMetadata", "CaseSections", "CaseChunks"]
    
    logger.info("Collection Statistics:")
    logger.info("=" * 60)
    
    for name in collection_names:
        if not client.collections.exists(name):
            logger.info(f"{name}: Does not exist")
            continue
        
        collection = client.collections.get(name)
        result = collection.aggregate.over_all()
        count = result.total_count
        
        logger.info(f"{name}: {count} objects")
    
    logger.info("=" * 60)
    client_wrapper.close()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Initialize Weaviate collections")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force recreate existing collections"
    )
    parser.add_argument(
        "--delete",
        action="store_true",
        help="Delete all collections (use with caution!)"
    )
    parser.add_argument(
        "--stats",
        action="store_true",
        help="Show collection statistics"
    )
    
    args = parser.parse_args()
    
    if args.delete:
        confirm = input("⚠️  Are you sure you want to delete all collections? (yes/no): ")
        if confirm.lower() == "yes":
            delete_all_collections()
        else:
            logger.info("Deletion cancelled")
    elif args.stats:
        get_collection_stats()
    else:
        success = init_weaviate(force_recreate=args.force)
        sys.exit(0 if success else 1)
