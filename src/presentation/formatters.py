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
from rich.align import Align
from rich import box

from core.models import CaseMetadata, ExtractedFacts, SimilarCase, BatchIngestResult

console = Console()


class RichFormatter:
    """Formats output using Rich library for beautiful CLI."""
    
    # Professional color scheme
    colors = {
        'primary': "#c2edff",
        'secondary': "#dbcffe",
        'success': '#34d399',
        'warning': '#fbbf24',
        'error': '#f87171',
        'info': "#61a8ff",
        'text': '#f8fafc',
        'muted': '#9ca3af',
        'accent': '#10b981',
        'gold': '#f59e0b',
    }
    
    @staticmethod
    def display_welcome():
        """Display welcome screen with ASCII art logo."""
        console.clear()
        
        logo = Text()
        logo.append("╔═════════════════════════════════════════════════════════════════════════════════════════════════════════╗\n", style=RichFormatter.colors['primary'])
        logo.append("║                                                                                                         ║\n", style=RichFormatter.colors['primary'])
        logo.append("║                                                                                                         ║\n", style=RichFormatter.colors['primary'])
        logo.append("║                     ██████╗ █████╗ ███████╗███████╗███╗   ███╗██╗███╗   ██╗██████╗                      ║\n", style=f"bold {RichFormatter.colors['primary']}")
        logo.append("║                    ██╔════╝██╔══██╗██╔════╝██╔════╝████╗ ████║██║████╗  ██║██╔══██╗                     ║\n", style=f"bold {RichFormatter.colors['primary']}")
        logo.append("║                    ██║     ███████║███████╗█████╗  ██╔████╔██║██║██╔██╗ ██║██║  ██║                     ║\n", style=f"bold {RichFormatter.colors['primary']}")
        logo.append("║                    ██║     ██╔══██║╚════██║██╔══╝  ██║╚██╔╝██║██║██║╚██╗██║██║  ██║                     ║\n", style=f"bold {RichFormatter.colors['primary']}")
        logo.append("║                    ╚██████╗██║  ██║███████║███████╗██║ ╚═╝ ██║██║██║ ╚████║██████╔╝                     ║\n", style=f"bold {RichFormatter.colors['primary']}")
        logo.append("║                     ╚═════╝╚═╝  ╚═╝╚══════╝╚══════╝╚═╝     ╚═╝╚═╝╚═╝  ╚═══╝╚═════╝                      ║\n", style=f"bold {RichFormatter.colors['primary']}")
        logo.append("║                                                                                                         ║\n", style=RichFormatter.colors['primary'])
        logo.append("║                                    Legal Similarity Search & Analysis                                   ║\n", style=RichFormatter.colors['secondary'])
        logo.append("║                              AI-Powered Case Matching with Haystack + pgvector                         ║\n", style=RichFormatter.colors['secondary'])
        logo.append("║                                                                                                         ║\n", style=RichFormatter.colors['primary'])
        logo.append("║               ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━            ║\n", style=RichFormatter.colors['primary'])
        logo.append("║                                                  Features                                               ║\n", style=RichFormatter.colors['text'])
        logo.append("║                                                                                                         ║\n", style=f"bold {RichFormatter.colors['primary']}")
        logo.append("║  • Semantic similarity using dual embeddings           • Cross-encoder re-ranking for precision         ║\n", style=RichFormatter.colors['info'])
        logo.append("║  • Intelligent threshold-based filtering               • PostgreSQL + pgvector for fast search          ║\n", style=RichFormatter.colors['info'])
        logo.append("║                                                                                                         ║\n", style=RichFormatter.colors['primary'])
        logo.append("╚═════════════════════════════════════════════════════════════════════════════════════════════════════════╝", style=RichFormatter.colors['primary'])
        
        console.print(Align.center(logo))
        console.print()
    
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
    def get_similarity_color(score: float) -> str:
        """Get color for similarity score."""
        if score >= 0.9:
            return RichFormatter.colors['success']
        elif score >= 0.8:
            return RichFormatter.colors['accent']
        elif score >= 0.7:
            return RichFormatter.colors['info']
        elif score >= 0.6:
            return RichFormatter.colors['gold']
        elif score >= 0.5:
            return RichFormatter.colors['warning']
        else:
            return RichFormatter.colors['error']
    
    @staticmethod
    def get_similarity_bar(score: float, width: int = 20) -> str:
        """Create visual bar for similarity score."""
        filled = int(score * width)
        empty = width - filled
        return '█' * filled + '░' * empty
    
    @staticmethod
    def format_similar_cases(similar_cases: List[SimilarCase]) -> Table:
        """
        Format similar cases as a table with visual bars.
        
        Args:
            similar_cases: List of SimilarCase objects
            
        Returns:
            Rich Table
        """
        table = Table(
            title="🔍 Similar Cases",
            show_lines=True,
            box=box.ROUNDED,
            border_style=RichFormatter.colors['primary'],
            header_style=f"bold {RichFormatter.colors['primary']}"
        )
        
        table.add_column("Rank", justify="center", style="bold", width=6)
        table.add_column("Case Title", style=RichFormatter.colors['text'], width=30)
        table.add_column("Court", style=RichFormatter.colors['text'], width=18)
        table.add_column("Sections", style=RichFormatter.colors['text'], width=12)
        table.add_column("CE Score", justify="center", width=10)
        table.add_column("Visual", justify="left", width=12)
        table.add_column("Cosine", justify="center", width=8)
        
        for i, case in enumerate(similar_cases, 1):
            sections = ', '.join(case.sections_invoked[:2])  # Show first 2
            if len(case.sections_invoked) > 2:
                sections += "..."
            
            # Get colors and bars
            ce_color = RichFormatter.get_similarity_color(case.cross_encoder_score)
            cos_color = RichFormatter.get_similarity_color(case.cosine_similarity)
            bar = RichFormatter.get_similarity_bar(case.cross_encoder_score, width=8)
            
            # Truncate case title
            title = case.case_title[:28] + "..." if len(case.case_title) > 28 else case.case_title
            court = case.court_name[:16] + "..." if len(case.court_name) > 16 else case.court_name
            
            table.add_row(
                str(i),
                title,
                court,
                sections,
                f"[{ce_color}]{case.cross_encoder_score:.3f}[/{ce_color}]",
                f"[{ce_color}]{bar}[/{ce_color}]",
                f"[{cos_color}]{case.cosine_similarity:.3f}[/{cos_color}]"
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
