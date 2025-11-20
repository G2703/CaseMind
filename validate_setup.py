"""
Validation script to check CaseMind installation.
Run this after setup to verify all components are working.
"""

import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()


def check_python_version():
    """Check Python version >= 3.9"""
    version = sys.version_info
    if version.major == 3 and version.minor >= 9:
        return True, f"{version.major}.{version.minor}.{version.micro}"
    return False, f"{version.major}.{version.minor}.{version.micro} (requires 3.9+)"


def check_environment_file():
    """Check if .env file exists"""
    env_file = Path(__file__).parent / ".env"
    return env_file.exists(), str(env_file)


def check_imports():
    """Check if all required packages are installed"""
    packages = [
        ("openai", "OpenAI"),
        ("sentence_transformers", "Sentence Transformers"),
        ("psycopg2", "psycopg2"),
        ("pgvector.psycopg2", "pgvector"),
        ("fitz", "PyMuPDF"),
        ("rich", "Rich"),
        ("dotenv", "python-dotenv"),
    ]
    
    results = {}
    for import_name, display_name in packages:
        try:
            __import__(import_name)
            results[display_name] = (True, "Installed")
        except ImportError as e:
            results[display_name] = (False, f"Missing: {str(e)}")
    
    return results


def check_directories():
    """Check if required directories exist"""
    base = Path(__file__).parent
    dirs = {
        "Source Code": base / "src",
        "Templates": base / "templates",
        "Ontology Schema": base / "Ontology_schema",
        "Logs": base / "logs",
    }
    
    results = {}
    for name, path in dirs.items():
        results[name] = (path.exists(), str(path))
    
    return results


def check_config_files():
    """Check if required config files exist"""
    base = Path(__file__).parent
    files = {
        "config.json": base / "config.json",
        "ontology_schema.json": base / "Ontology_schema" / "ontology_schema.json",
    }
    
    results = {}
    for name, path in files.items():
        results[name] = (path.exists(), str(path))
    
    return results


def check_database_connection():
    """Check database connection"""
    try:
        from src.core.config import Config
        from src.infrastructure.document_store import PGVectorDocumentStore
        
        config = Config()
        store = PGVectorDocumentStore()
        stats = store.get_statistics()
        
        return True, f"Connected ({stats.get('total_cases', 0)} cases)"
    except Exception as e:
        return False, str(e)


def check_models():
    """Check if models can be loaded"""
    try:
        from src.services.embedding_service import EmbeddingService
        
        embedder = EmbeddingService()
        test_embedding = embedder.embed_query("test")
        
        if len(test_embedding) == 768:
            return True, "Embedding model loaded (768-dim)"
        else:
            return False, f"Unexpected embedding size: {len(test_embedding)}"
    except Exception as e:
        return False, str(e)


def main():
    """Run all validation checks"""
    console.print("\n")
    console.print(Panel.fit(
        "[bold blue]CaseMind Installation Validator[/bold blue]",
        border_style="blue"
    ))
    console.print("\n")
    
    all_passed = True
    
    # Check Python version
    console.print("[bold cyan]Checking Python version...[/bold cyan]")
    passed, info = check_python_version()
    status = "[green]✓[/green]" if passed else "[red]✗[/red]"
    console.print(f"  {status} Python {info}")
    all_passed &= passed
    console.print()
    
    # Check environment file
    console.print("[bold cyan]Checking configuration files...[/bold cyan]")
    passed, path = check_environment_file()
    status = "[green]✓[/green]" if passed else "[red]✗[/red]"
    console.print(f"  {status} .env file")
    if not passed:
        console.print(f"      [yellow]Copy .env.example to .env[/yellow]")
    all_passed &= passed
    console.print()
    
    # Check config files
    console.print("[bold cyan]Checking required files...[/bold cyan]")
    config_results = check_config_files()
    for name, (passed, path) in config_results.items():
        status = "[green]✓[/green]" if passed else "[red]✗[/red]"
        console.print(f"  {status} {name}")
        if not passed:
            console.print(f"      [yellow]{path}[/yellow]")
        all_passed &= passed
    console.print()
    
    # Check directories
    console.print("[bold cyan]Checking directory structure...[/bold cyan]")
    dir_results = check_directories()
    for name, (passed, path) in dir_results.items():
        status = "[green]✓[/green]" if passed else "[red]✗[/red]"
        console.print(f"  {status} {name}")
        if not passed:
            console.print(f"      [yellow]{path}[/yellow]")
        all_passed &= passed
    console.print()
    
    # Check Python packages
    console.print("[bold cyan]Checking Python packages...[/bold cyan]")
    package_results = check_imports()
    for name, (passed, info) in package_results.items():
        status = "[green]✓[/green]" if passed else "[red]✗[/red]"
        console.print(f"  {status} {name}")
        if not passed:
            console.print(f"      [yellow]{info}[/yellow]")
            console.print(f"      [yellow]Install: pip install {name}[/yellow]")
        all_passed &= passed
    console.print()
    
    # Check database
    console.print("[bold cyan]Checking database connection...[/bold cyan]")
    passed, info = check_database_connection()
    status = "[green]✓[/green]" if passed else "[red]✗[/red]"
    console.print(f"  {status} PostgreSQL Database")
    if passed:
        console.print(f"      {info}")
    else:
        console.print(f"      [yellow]{info}[/yellow]")
        console.print(f"      [yellow]Run: python src/scripts/init_database.py[/yellow]")
    all_passed &= passed
    console.print()
    
    # Check models
    console.print("[bold cyan]Checking AI models...[/bold cyan]")
    passed, info = check_models()
    status = "[green]✓[/green]" if passed else "[red]✗[/red]"
    console.print(f"  {status} Embedding Service")
    if passed:
        console.print(f"      {info}")
    else:
        console.print(f"      [yellow]{info}[/yellow]")
    all_passed &= passed
    console.print()
    
    # Final summary
    console.print()
    if all_passed:
        console.print(Panel.fit(
            "[bold green]✓ All checks passed! CaseMind is ready to use.[/bold green]\n\n"
            "Run: [cyan]python src/main.py[/cyan]",
            border_style="green"
        ))
    else:
        console.print(Panel.fit(
            "[bold yellow]⚠ Some checks failed. Please fix the issues above.[/bold yellow]\n\n"
            "See QUICKSTART.md for detailed setup instructions.",
            border_style="yellow"
        ))
    console.print()
    
    return all_passed


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
