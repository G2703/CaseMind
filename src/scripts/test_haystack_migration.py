"""
Test script for Haystack 2.0 migration.
Validates that new Haystack components work correctly.
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

console = Console()
logging.basicConfig(level=logging.INFO)


async def test_haystack_components():
    """Test Haystack components."""
    console.print(Panel.fit("[bold cyan]Testing Haystack 2.0 Components[/]", border_style="cyan"))
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        
        # Test 1: Document Store
        task = progress.add_task("Testing Haystack Document Store...", total=None)
        try:
            from infrastructure.haystack_document_store import HaystackDocumentStoreWrapper
            
            store = HaystackDocumentStoreWrapper()
            stats = store.get_statistics()
            
            progress.update(task, description=f"✓ Document Store: {stats['total_documents']} documents")
            console.print(f"[green]✓ HaystackDocumentStoreWrapper initialized successfully[/]")
            console.print(f"  Backend: {stats['backend']}")
            console.print(f"  Total documents: {stats['total_documents']}")
            console.print()
        except Exception as e:
            progress.update(task, description=f"✗ Document Store failed")
            console.print(f"[red]✗ Error: {e}[/]")
            return False
        
        # Test 2: Embedding Service
        task = progress.add_task("Testing Haystack Embedding Service...", total=None)
        try:
            from services.haystack_embedding_service import HaystackEmbeddingService
            
            embedder = HaystackEmbeddingService()
            test_embedding = embedder.embed_text("Test legal case")
            
            progress.update(task, description=f"✓ Embedding Service: {len(test_embedding)}-dim vectors")
            console.print(f"[green]✓ HaystackEmbeddingService initialized successfully[/]")
            console.print(f"  Model: {embedder.model_name}")
            console.print(f"  Embedding dimension: {len(test_embedding)}")
            console.print()
        except Exception as e:
            progress.update(task, description=f"✗ Embedding Service failed")
            console.print(f"[red]✗ Error: {e}[/]")
            return False
        
        # Test 3: Ranker Service
        task = progress.add_task("Testing Haystack Ranker Service...", total=None)
        try:
            from services.haystack_ranker_service import HaystackRankerService
            from haystack import Document
            
            ranker = HaystackRankerService()
            
            # Test ranking
            test_docs = [
                Document(content="IPC Section 302 murder case", id="doc1"),
                Document(content="Civil property dispute", id="doc2"),
            ]
            ranked = ranker.rank_documents("murder case IPC 302", test_docs, top_k=2)
            
            progress.update(task, description=f"✓ Ranker Service: Ranked {len(ranked)} documents")
            console.print(f"[green]✓ HaystackRankerService initialized successfully[/]")
            console.print(f"  Model: {ranker.model_name}")
            console.print(f"  Test ranking scores: {[f'{d.score:.3f}' for d in ranked]}")
            console.print()
        except Exception as e:
            progress.update(task, description=f"✗ Ranker Service failed")
            console.print(f"[red]✗ Error: {e}[/]")
            return False
        
        # Test 4: Document Converter
        task = progress.add_task("Testing Haystack Document Converter...", total=None)
        try:
            from infrastructure.haystack_document_converter import HaystackDocumentConverter
            import numpy as np
            
            converter = HaystackDocumentConverter()
            
            # Test conversion
            test_embedding = np.random.rand(768).tolist()
            haystack_doc = converter.to_haystack_document(
                doc_id="test_123",
                content="Test case content",
                metadata={"case_title": "Test v. State", "case_id": "test_123"},
                embedding_facts=test_embedding,
                file_hash="abc123"
            )
            
            # Convert back
            converted_back = converter.from_haystack_document(haystack_doc)
            
            progress.update(task, description=f"✓ Document Converter: Bidirectional conversion working")
            console.print(f"[green]✓ HaystackDocumentConverter working correctly[/]")
            console.print(f"  Converted document ID: {haystack_doc.id}")
            console.print(f"  Metadata preserved: {bool(converted_back['meta'])}")
            console.print()
        except Exception as e:
            progress.update(task, description=f"✗ Document Converter failed")
            console.print(f"[red]✗ Error: {e}[/]")
            return False
        
        # Test 5: Pipeline
        task = progress.add_task("Testing Haystack Similarity Pipeline...", total=None)
        try:
            from pipelines.haystack_similarity_pipeline import HaystackSimilarityPipeline
            
            pipeline = HaystackSimilarityPipeline()
            
            # Get pipeline structure
            # Note: pipeline.get_pipeline_graph() shows the structure
            
            progress.update(task, description=f"✓ Similarity Pipeline: Initialized")
            console.print(f"[green]✓ HaystackSimilarityPipeline initialized successfully[/]")
            console.print(f"  Top-k: {pipeline.top_k}")
            console.print(f"  Threshold: {pipeline.threshold}")
            console.print()
            
            # Show pipeline graph
            console.print(Panel("[bold]Pipeline Structure:[/]\n" + str(pipeline.retrieval_pipeline), 
                                title="Haystack Pipeline", border_style="blue"))
            console.print()
            
        except Exception as e:
            progress.update(task, description=f"✗ Similarity Pipeline failed")
            console.print(f"[red]✗ Error: {e}[/]")
            return False
    
    return True


async def test_integration():
    """Test full integration."""
    console.print(Panel.fit("[bold magenta]Full Integration Test[/]", border_style="magenta"))
    console.print()
    
    try:
        from infrastructure.haystack_document_store import HaystackDocumentStoreWrapper
        from services.haystack_embedding_service import HaystackEmbeddingService
        
        store = HaystackDocumentStoreWrapper()
        embedder = HaystackEmbeddingService()
        
        # Test embedding and storage workflow
        console.print("[cyan]Testing document storage workflow...[/]")
        
        test_text = "Test case involving IPC Section 302 murder charge"
        test_embedding = embedder.embed_text(test_text)
        
        console.print(f"[green]✓ Generated embedding: {test_embedding.shape}[/]")
        console.print()
        
        # Test retrieval workflow
        console.print("[cyan]Testing retrieval workflow...[/]")
        
        stats = store.get_statistics()
        if stats['total_documents'] > 0:
            # Try a query
            results = store.query_by_embedding(
                embedding=test_embedding,
                top_k=3,
                embedding_field="embedding_facts"
            )
            console.print(f"[green]✓ Retrieved {len(results)} similar documents[/]")
            if results:
                console.print(f"  Top result: {results[0]['meta'].get('case_title', 'Unknown')}")
        else:
            console.print(f"[yellow]⚠ No documents in database for retrieval test[/]")
        
        console.print()
        
        return True
        
    except Exception as e:
        console.print(f"[red]✗ Integration test failed: {e}[/]")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all tests."""
    console.print()
    console.print("[bold cyan]═" * 60 + "[/]")
    console.print("[bold cyan]  Haystack 2.0 Migration Test Suite[/]")
    console.print("[bold cyan]═" * 60 + "[/]")
    console.print()
    
    # Test components
    components_ok = await test_haystack_components()
    
    if not components_ok:
        console.print()
        console.print(Panel(
            "[bold red]Component tests failed![/]\n\n"
            "Please check the error messages above and ensure:\n"
            "1. All dependencies are installed (pip install -r requirements.txt)\n"
            "2. PostgreSQL is running with pgvector extension\n"
            "3. Database connection settings are correct in .env",
            title="Test Failed",
            border_style="red"
        ))
        return
    
    # Test integration
    integration_ok = await test_integration()
    
    console.print()
    
    if components_ok and integration_ok:
        console.print(Panel.fit(
            "[bold green]✓ All Tests Passed![/]\n\n"
            "Haystack 2.0 components are working correctly.\n"
            "You can now use the new implementation in your application.\n\n"
            "Next steps:\n"
            "1. Review HAYSTACK_INTEGRATION.md for usage guide\n"
            "2. Update your code to use Haystack components\n"
            "3. Run python src/scripts/haystack_migration_report.py for full details",
            title="Success",
            border_style="green"
        ))
    else:
        console.print(Panel(
            "[bold yellow]⚠ Some tests failed[/]\n\n"
            "Please review the errors above and fix any issues.",
            title="Warning",
            border_style="yellow"
        ))
    
    console.print()


if __name__ == "__main__":
    asyncio.run(main())
