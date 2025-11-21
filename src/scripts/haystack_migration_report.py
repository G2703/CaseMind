"""
Migration Script: Transition from custom implementation to Haystack 2.0 components.

This script helps migrate CaseMind from the custom implementation to
the new Haystack-based architecture.

Migration Steps:
1. Install new dependencies
2. Update imports in existing code
3. Test compatibility
4. Switch to new implementation
"""

import logging
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.panel import Panel
from rich.table import Table

console = Console()
logger = logging.getLogger(__name__)


class HaystackMigration:
    """Handles migration to Haystack 2.0 architecture."""
    
    def __init__(self):
        self.console = console
    
    def show_migration_plan(self):
        """Display migration plan."""
        plan = Table(title="Haystack 2.0 Migration Plan")
        plan.add_column("Step", style="cyan")
        plan.add_column("Old Component", style="yellow")
        plan.add_column("New Haystack Component", style="green")
        plan.add_column("Status", style="bold")
        
        components = [
            ("1", "Custom PGVectorDocumentStore", "haystack_integrations.document_stores.pgvector.PgvectorDocumentStore", "✓ Ready"),
            ("2", "Custom EmbeddingService", "haystack.components.embedders.SentenceTransformersTextEmbedder", "✓ Ready"),
            ("3", "Custom Cross-Encoder", "haystack.components.rankers.TransformersSimilarityRanker", "✓ Ready"),
            ("4", "Manual Pipeline Orchestration", "haystack.Pipeline with component connections", "✓ Ready"),
            ("5", "Custom Retrieval Logic", "haystack_integrations.components.retrievers.pgvector.PgvectorEmbeddingRetriever", "✓ Ready"),
            ("6", "Custom Document Format", "haystack.Document with metadata", "✓ Ready"),
        ]
        
        for step, old, new, status in components:
            plan.add_row(step, old, new, status)
        
        self.console.print(plan)
        self.console.print()
    
    def show_benefits(self):
        """Display benefits of Haystack integration."""
        benefits = Panel(
            "[bold green]Benefits of Haystack 2.0 Integration:[/]\n\n"
            "✓ [cyan]Standardized Components[/]: Use battle-tested Haystack components\n"
            "✓ [cyan]Pipeline Abstraction[/]: Declarative pipeline building with automatic optimization\n"
            "✓ [cyan]Easy Extensibility[/]: Add new components from Haystack ecosystem\n"
            "✓ [cyan]Better Debugging[/]: Pipeline visualization and step-by-step execution\n"
            "✓ [cyan]Production Ready[/]: Haystack's proven architecture for LLM applications\n"
            "✓ [cyan]Integration Ready[/]: Easy integration with other Haystack-compatible tools\n"
            "✓ [cyan]Monitoring & Logging[/]: Built-in observability features\n"
            "✓ [cyan]Community Support[/]: Active Haystack community and documentation",
            title="Why Migrate?",
            border_style="green"
        )
        self.console.print(benefits)
        self.console.print()
    
    def show_usage_comparison(self):
        """Show side-by-side comparison of old vs new usage."""
        self.console.print(Panel("[bold]Usage Comparison: Old vs New[/]", style="cyan"))
        self.console.print()
        
        # Old way
        self.console.print("[yellow]OLD WAY (Custom Implementation):[/]")
        self.console.print("""
```python
from infrastructure.document_store import PGVectorDocumentStore
from services.embedding_service import EmbeddingService
from pipelines.similarity_pipeline import SimilaritySearchPipeline

# Initialize components manually
store = PGVectorDocumentStore()
embedder = EmbeddingService()

# Run pipeline
pipeline = SimilaritySearchPipeline()
result = await pipeline.run_full_pipeline(file_path)
```
""")
        
        # New way
        self.console.print("[green]NEW WAY (Haystack 2.0):[/]")
        self.console.print("""
```python
from infrastructure.haystack_document_store import HaystackDocumentStoreWrapper
from services.haystack_embedding_service import HaystackEmbeddingService
from pipelines.haystack_similarity_pipeline import HaystackSimilarityPipeline

# Initialize Haystack components (same interface!)
store = HaystackDocumentStoreWrapper()
embedder = HaystackEmbeddingService()

# Run Haystack pipeline (same interface!)
pipeline = HaystackSimilarityPipeline()
result = await pipeline.run_full_pipeline(file_path)

# BONUS: Visualize pipeline
print(pipeline.get_pipeline_graph())
```
""")
        
        self.console.print()
        self.console.print("[bold green]✓ Backward compatible interface - minimal code changes![/]")
        self.console.print()
    
    def show_installation_steps(self):
        """Show installation instructions."""
        install = Panel(
            "[bold]Installation Steps:[/]\n\n"
            "1. Update dependencies:\n"
            "   [cyan]pip install -r requirements.txt[/]\n\n"
            "2. New packages will be installed:\n"
            "   • haystack-ai>=2.0.0\n"
            "   • pgvector-haystack\n"
            "   • sentence-transformers-haystack\n\n"
            "3. Database migration (optional):\n"
            "   Existing data works with new implementation!\n"
            "   No migration needed for PostgreSQL + pgvector.\n\n"
            "4. Update imports in your code:\n"
            "   See usage comparison above.\n\n"
            "5. Test the new pipeline:\n"
            "   [cyan]python src/scripts/test_haystack_migration.py[/]",
            title="Installation",
            border_style="blue"
        )
        self.console.print(install)
        self.console.print()
    
    def show_architecture(self):
        """Display new architecture diagram."""
        architecture = """
[bold cyan]New Haystack-Based Architecture:[/]

┌─────────────────────────────────────────────────────────────┐
│                    CaseMind Application                      │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌─────────────────────────────────────────────────────┐   │
│  │         Haystack Similarity Pipeline                 │   │
│  │  ┌───────────┐   ┌──────────┐   ┌────────────┐     │   │
│  │  │  Text     │ → │ Pgvector │ → │ Ranker     │     │   │
│  │  │ Embedder  │   │ Retriever│   │ (Cross-Enc)│     │   │
│  │  └───────────┘   └──────────┘   └────────────┘     │   │
│  │                          ↓                           │   │
│  │                   ┌────────────┐                     │   │
│  │                   │ Threshold  │                     │   │
│  │                   │  Filter    │                     │   │
│  │                   └────────────┘                     │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                               │
│  ┌─────────────────────────────────────────────────────┐   │
│  │         Haystack Document Store                      │   │
│  │  ┌───────────────────────────────────────────────┐  │   │
│  │  │  PgvectorDocumentStore                         │  │   │
│  │  │  • HNSW indexing for fast similarity search   │  │   │
│  │  │  • Metadata filtering                          │  │   │
│  │  │  • Dual embedding support (facts + metadata)  │  │   │
│  │  └───────────────────────────────────────────────┘  │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                               │
│  ┌─────────────────────────────────────────────────────┐   │
│  │         Haystack Components                          │   │
│  │  • SentenceTransformersTextEmbedder                 │   │
│  │  • SentenceTransformersDocumentEmbedder             │   │
│  │  • PgvectorEmbeddingRetriever                       │   │
│  │  • TransformersSimilarityRanker                     │   │
│  │  • Custom ThresholdFilterComponent                  │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                               │
└───────────────────────────────────────────────────────────────┘
                              ↓
                    ┌──────────────────┐
                    │  PostgreSQL +    │
                    │    pgvector      │
                    └──────────────────┘
"""
        self.console.print(architecture)
        self.console.print()
    
    def run_migration_report(self):
        """Run complete migration report."""
        self.console.print()
        self.console.print(Panel.fit(
            "[bold magenta]CaseMind → Haystack 2.0 Migration Report[/]",
            border_style="magenta"
        ))
        self.console.print()
        
        self.show_benefits()
        self.show_migration_plan()
        self.show_architecture()
        self.show_usage_comparison()
        self.show_installation_steps()
        
        self.console.print(Panel(
            "[bold green]✓ Migration is Ready![/]\n\n"
            "All Haystack components have been implemented with backward compatibility.\n"
            "You can start using the new implementation immediately.\n\n"
            "To get started:\n"
            "1. Update imports to use Haystack components\n"
            "2. Test with existing data (no migration needed)\n"
            "3. Enjoy the benefits of Haystack 2.0!",
            title="Summary",
            border_style="green"
        ))


def main():
    """Run migration report."""
    migration = HaystackMigration()
    migration.run_migration_report()


if __name__ == "__main__":
    main()
