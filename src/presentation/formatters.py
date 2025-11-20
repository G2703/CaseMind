"""
Rich library formatters for CLI output.
"""

from typing import List, Dict, Any
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.markdown import Markdown
from rich.text import Text

from core.models import CaseMetadata, ExtractedFacts, SimilarCase, BatchIngestResult

console = Console()


class RichFormatter:
    """Formats output using Rich library for beautiful CLI."""
    
    @staticmethod
    def display_welcome():
        """Display welcome banner."""
        welcome_text = """
# CaseMind Legal Similarity Search

AI-powered similarity search for legal cases using Haystack + pgvector
        """
        console.print(Panel(Markdown(welcome_text), border_style="bold blue"))
    
    @staticmethod
    def display_menu():
        """Display main menu."""
        menu_table = Table(show_header=False, box=None, padding=(0, 2))
        menu_table.add_column("Option", style="cyan bold", width=8)
        menu_table.add_column("Description", style="white")
        
        menu_table.add_row("1", "Ingest Cases (Batch)")
        menu_table.add_row("2", "Find Similar Cases")
        menu_table.add_row("3", "Database Statistics")
        menu_table.add_row("4", "Health Check")
        menu_table.add_row("5", "Exit")
        
        console.print("\n")
        console.print(menu_table)
        console.print("\n")
    
    @staticmethod
    def format_metadata(metadata: CaseMetadata) -> Panel:
        """
        Format case metadata as a panel.
        
        Args:
            metadata: CaseMetadata object
            
        Returns:
            Rich Panel
        """
        content = f"""[bold cyan]Case Title:[/bold cyan] {metadata.case_title}
[bold cyan]Case ID:[/bold cyan] {metadata.case_id}
[bold cyan]Court:[/bold cyan] {metadata.court_name}
[bold cyan]Judgment Date:[/bold cyan] {metadata.judgment_date}
[bold cyan]Sections Invoked:[/bold cyan] {', '.join(metadata.sections_invoked)}
[bold cyan]Most Appropriate Section:[/bold cyan] {metadata.most_appropriate_section}"""
        
        return Panel(content, title="📋 Case Metadata", border_style="green")
    
    @staticmethod
    def format_facts(facts: ExtractedFacts) -> Panel:
        """
        Format extracted facts as a panel.
        
        Args:
            facts: ExtractedFacts object
            
        Returns:
            Rich Panel
        """
        content = f"""[bold yellow]Tier 1 - Parties:[/bold yellow]
{facts.tier_1_parties}

[bold yellow]Tier 2 - Incident Details:[/bold yellow]
{facts.tier_2_incident}

[bold yellow]Tier 3 - Legal Aspects:[/bold yellow]
{facts.tier_3_legal}

[bold yellow]Tier 4 - Procedural History:[/bold yellow]
{facts.tier_4_procedural}"""
        
        return Panel(content, title="📝 Extracted Facts", border_style="yellow")
    
    @staticmethod
    def format_facts_summary(facts_summary: str) -> Panel:
        """
        Format facts summary as a panel.
        
        Args:
            facts_summary: Summary text
            
        Returns:
            Rich Panel
        """
        return Panel(
            facts_summary, 
            title="📝 Facts Summary", 
            border_style="yellow"
        )
    
    @staticmethod
    def format_similar_cases(similar_cases: List[SimilarCase]) -> Table:
        """
        Format similar cases as a table.
        
        Args:
            similar_cases: List of SimilarCase objects
            
        Returns:
            Rich Table
        """
        table = Table(title="🔍 Similar Cases", show_lines=True)
        
        table.add_column("Rank", style="cyan bold", width=6)
        table.add_column("Case Title", style="white", width=40)
        table.add_column("Court", style="green", width=20)
        table.add_column("Date", style="blue", width=12)
        table.add_column("Sections", style="magenta", width=15)
        table.add_column("Score", style="yellow", width=10)
        
        for i, case in enumerate(similar_cases, 1):
            sections = ', '.join(case.sections_invoked[:3])  # Show first 3
            if len(case.sections_invoked) > 3:
                sections += "..."
            
            score_color = "green" if case.cross_encoder_score > 0.7 else "yellow"
            
            table.add_row(
                str(i),
                case.case_title[:40] + "..." if len(case.case_title) > 40 else case.case_title,
                case.court_name[:20],
                case.judgment_date,
                sections,
                f"[{score_color}]{case.cross_encoder_score:.3f}[/{score_color}]"
            )
        
        return table
    
    @staticmethod
    def format_batch_result(result: BatchIngestResult) -> Panel:
        """
        Format batch ingestion result.
        
        Args:
            result: BatchIngestResult object
            
        Returns:
            Rich Panel
        """
        success_rate = (result.processed / result.total_files * 100) if result.total_files > 0 else 0
        
        content = f"""[bold green]✓ Processed:[/bold green] {result.processed} / {result.total_files}
[bold yellow]⊘ Skipped (Duplicates):[/bold yellow] {result.skipped_duplicates}
[bold red]✗ Failed:[/bold red] {result.failed}
[bold cyan]Success Rate:[/bold cyan] {success_rate:.1f}%"""
        
        if result.errors:
            content += f"\n\n[bold red]Errors:[/bold red]\n"
            for error in result.errors[:5]:  # Show first 5 errors
                content += f"  • {error}\n"
            if len(result.errors) > 5:
                content += f"  ... and {len(result.errors) - 5} more"
        
        border_style = "green" if result.failed == 0 else "yellow"
        
        return Panel(content, title="📊 Batch Ingestion Results", border_style=border_style)
    
    @staticmethod
    def format_statistics(stats: Dict[str, Any]) -> Table:
        """
        Format database statistics.
        
        Args:
            stats: Statistics dictionary
            
        Returns:
            Rich Table
        """
        table = Table(title="📊 Database Statistics", show_header=False)
        table.add_column("Metric", style="cyan bold", width=30)
        table.add_column("Value", style="white", width=20)
        
        # Map database column names to display names
        table.add_row("Total Cases", str(stats.get('total_documents', 0)))
        table.add_row("Unique Templates", str(stats.get('unique_templates', 0)))
        table.add_row("Oldest Case", str(stats.get('oldest_case', 'N/A')))
        table.add_row("Newest Case", str(stats.get('newest_case', 'N/A')))
        table.add_row("Database Size", stats.get('database_size', 'N/A'))
        
        return table
    
    @staticmethod
    def display_progress_bar(total: int, description: str = "Processing"):
        """
        Create a progress bar context.
        
        Args:
            total: Total items
            description: Description text
            
        Returns:
            Progress context manager
        """
        return Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console
        )
    
    @staticmethod
    def print_success(message: str):
        """Print success message."""
        console.print(f"[bold green]✓[/bold green] {message}")
    
    @staticmethod
    def print_error(message: str):
        """Print error message."""
        console.print(f"[bold red]✗[/bold red] {message}")
    
    @staticmethod
    def print_warning(message: str):
        """Print warning message."""
        console.print(f"[bold yellow]⚠[/bold yellow] {message}")
    
    @staticmethod
    def print_info(message: str):
        """Print info message."""
        console.print(f"[bold cyan]ℹ[/bold cyan] {message}")
    
    @staticmethod
    def display_health_status(status: Dict[str, Any]):
        """
        Display health check status.
        
        Args:
            status: Health status dictionary
        """
        all_healthy = all(status.values())
        
        table = Table(title="🏥 System Health Check", show_header=True)
        table.add_column("Component", style="cyan bold", width=30)
        table.add_column("Status", width=15)
        
        for component, healthy in status.items():
            status_text = "[bold green]✓ Healthy[/bold green]" if healthy else "[bold red]✗ Unhealthy[/bold red]"
            table.add_row(component, status_text)
        
        console.print(table)
        
        if all_healthy:
            console.print("\n[bold green]All systems operational![/bold green]\n")
        else:
            console.print("\n[bold red]Some components need attention![/bold red]\n")
