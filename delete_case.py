"""
Delete a case and all its related data from Weaviate.
"""

import sys
import os
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.'))

from src.infrastructure.weaviate_client import WeaviateClient
from src.utils.logger import get_logger
from weaviate.classes.query import Filter

logger = get_logger(__name__)


def delete_case_by_file_id(file_id: str):
    """
    Delete all objects related to a file_id from all collections.
    
    Args:
        file_id: The file_id to delete
    """
    client_wrapper = WeaviateClient()
    client = client_wrapper.client
    
    collections = {
        "CaseDocuments": "file_id",
        "CaseMetadata": "file_id", 
        "CaseSections": "file_id",
        "CaseChunks": "file_id"
    }
    
    total_deleted = 0
    
    print(f"\nDeleting all data for file_id: {file_id}")
    print("=" * 60)
    
    for collection_name, filter_field in collections.items():
        try:
            collection = client.collections.get(collection_name)
            
            # Delete all objects matching the file_id
            result = collection.data.delete_many(
                where=Filter.by_property(filter_field).equal(file_id)
            )
            
            deleted_count = result.successful if hasattr(result, 'successful') else 0
            total_deleted += deleted_count
            
            print(f"{collection_name:20s} : {deleted_count} objects deleted")
            
        except Exception as e:
            logger.error(f"Error deleting from {collection_name}: {e}")
            print(f"{collection_name:20s} : Error - {e}")
    
    print("=" * 60)
    print(f"Total objects deleted: {total_deleted}")
    
    client_wrapper.close()
    return total_deleted


def list_all_cases():
    """List all cases with their file_ids."""
    client_wrapper = WeaviateClient()
    client = client_wrapper.client
    
    collection = client.collections.get("CaseDocuments")
    
    print("\n" + "=" * 80)
    print("ALL CASES IN DATABASE")
    print("=" * 80)
    
    results = collection.query.fetch_objects(limit=100)
    
    if not results.objects:
        print("No cases found in database.")
        client_wrapper.close()
        return
    
    for i, obj in enumerate(results.objects, 1):
        print(f"\n{i}. File ID: {obj.properties.get('file_id')}")
        print(f"   Filename: {obj.properties.get('original_filename')}")
        print(f"   Created: {obj.properties.get('created_at')}")
    
    print("=" * 80)
    client_wrapper.close()


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Delete case data from Weaviate")
    parser.add_argument(
        "--file-id",
        help="File ID to delete"
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List all cases with their file IDs"
    )
    
    args = parser.parse_args()
    
    if args.list:
        list_all_cases()
    elif args.file_id:
        confirm = input(f"\n⚠️  Delete all data for file_id '{args.file_id}'? (yes/no): ")
        if confirm.lower() == "yes":
            deleted = delete_case_by_file_id(args.file_id)
            if deleted > 0:
                print(f"\n✓ Successfully deleted case data")
            else:
                print(f"\n⚠️  No objects found for file_id: {args.file_id}")
        else:
            print("Deletion cancelled")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
