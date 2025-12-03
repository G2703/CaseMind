"""
Simple script to view Weaviate collections in table format.
"""

import sys
import os
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.'))

from src.infrastructure.weaviate_client import WeaviateClient
from src.utils.logger import get_logger

logger = get_logger(__name__)


def view_collection(collection_name: str, limit: int = 10):
    """View objects in a collection."""
    client_wrapper = WeaviateClient()
    client = client_wrapper.client
    
    try:
        collection = client.collections.get(collection_name)
        
        # Get total count
        result = collection.aggregate.over_all()
        total = result.total_count
        
        print(f"\n{'='*80}")
        print(f"Collection: {collection_name}")
        print(f"Total Objects: {total}")
        print(f"{'='*80}\n")
        
        if total == 0:
            print("No data yet. Ingest some files first!")
            return
        
        # Query objects
        response = collection.query.fetch_objects(limit=limit)
        
        if not response.objects:
            print("No objects found.")
            return
        
        # Display objects
        for i, obj in enumerate(response.objects, 1):
            print(f"\n--- Object {i} ---")
            print(f"UUID: {obj.uuid}")
            
            # Display properties
            for key, value in obj.properties.items():
                if isinstance(value, str) and len(value) > 100:
                    value = value[:100] + "..."
                print(f"  {key}: {value}")
            
            # Display vector info if present
            if obj.vector:
                print(f"  [Vector]: {len(obj.vector)} dimensions")
        
        if total > limit:
            print(f"\n... and {total - limit} more objects")
        
    except Exception as e:
        logger.error(f"Error viewing collection {collection_name}: {e}")
    finally:
        client_wrapper.close()


def view_all_collections():
    """View summary of all collections."""
    client_wrapper = WeaviateClient()
    client = client_wrapper.client
    
    collections = ["CaseDocuments", "CaseMetadata", "CaseSections", "CaseChunks"]
    
    print("\n" + "="*80)
    print("WEAVIATE COLLECTIONS SUMMARY")
    print("="*80)
    
    for name in collections:
        try:
            if client.collections.exists(name):
                collection = client.collections.get(name)
                result = collection.aggregate.over_all()
                count = result.total_count
                print(f"{name:20s} : {count:>6d} objects")
            else:
                print(f"{name:20s} : Does not exist")
        except Exception as e:
            print(f"{name:20s} : Error - {e}")
    
    print("="*80)
    client_wrapper.close()


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="View Weaviate collections")
    parser.add_argument(
        "--collection",
        choices=["CaseDocuments", "CaseMetadata", "CaseSections", "CaseChunks", "all"],
        default="all",
        help="Collection to view (default: all)"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Number of objects to display (default: 10)"
    )
    
    args = parser.parse_args()
    
    if args.collection == "all":
        view_all_collections()
        print("\nTo view details of a specific collection, use:")
        print("  python view_weaviate_data.py --collection CaseDocuments")
    else:
        view_collection(args.collection, args.limit)


if __name__ == "__main__":
    main()
