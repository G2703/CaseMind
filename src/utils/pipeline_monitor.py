"""
Pipeline Monitor - Detailed CLI dashboard with real-time progress tracking.
Uses rich library for beautiful progress bars and live updates.
"""

import asyncio
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, field

from rich.console import Console
from rich.progress import (
    Progress,
    SpinnerColumn,
    TextColumn,
    BarColumn,
    TaskProgressColumn,
    TimeRemainingColumn,
    TimeElapsedColumn,
)
from rich.table import Table
from rich.live import Live
from rich.panel import Panel
from rich.layout import Layout
from rich.text import Text

logger = logging.getLogger(__name__)


@dataclass
class StageMetrics:
    """Metrics for a pipeline stage."""
    name: str
    total: int = 0
    completed: int = 0
    failed: int = 0
    skipped: int = 0
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    current_file: str = ""
    rate_limit_info: str = ""
    
    @property
    def duration(self) -> Optional[timedelta]:
        """Get stage duration."""
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        elif self.start_time:
            return datetime.now() - self.start_time
        return None
    
    @property
    def success_rate(self) -> float:
        """Get success rate percentage."""
        if self.completed == 0:
            return 0.0
        return (self.completed / (self.completed + self.failed)) * 100


class PipelineMonitor:
    """
    Real-time pipeline monitor with detailed CLI dashboard.
    Displays progress bars, stage info, ETA, and metrics.
    """
    
    def __init__(self, total_files: int):
        """
        Initialize pipeline monitor.
        
        Args:
            total_files: Total number of files to process
        """
        self.total_files = total_files
        self.console = Console()
        
        # Stage metrics
        self.stages = {
            "pdf": StageMetrics("PDF Processing", total=total_files),
            "embedding": StageMetrics("Embedding Generation", total=total_files),
            "ingestion": StageMetrics("Weaviate Ingestion", total=total_files),
        }
        
        # Overall metrics
        self.start_time = datetime.now()
        self.current_stage = "initializing"
        
        # Progress bars
        self.progress: Optional[Progress] = None
        self.task_ids: Dict[str, int] = {}
        
        # Live display
        self.live: Optional[Live] = None
        
        logger.info(f"PipelineMonitor initialized for {total_files} files")
    
    def start(self) -> None:
        """Start the monitoring display."""
        # Create progress bars
        self.progress = Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TimeElapsedColumn(),
            TimeRemainingColumn(),
            console=self.console
        )
        
        # Add task for each stage
        for stage_name, metrics in self.stages.items():
            task_id = self.progress.add_task(
                f"{metrics.name}",
                total=metrics.total
            )
            self.task_ids[stage_name] = task_id
        
        # Start live display
        self.live = Live(
            self._create_layout(),
            console=self.console,
            refresh_per_second=2
        )
        self.live.start()
        
        logger.info("✓ Dashboard started")
    
    def stop(self) -> None:
        """Stop the monitoring display."""
        if self.live:
            self.live.stop()
        logger.info("✓ Dashboard stopped")
    
    async def update(self, stage: str, status: str, filename: str = "") -> None:
        """
        Update progress for a stage.
        
        Args:
            stage: Stage name (pdf, extraction, embedding, ingestion)
            status: Status update (started, completed, failed, etc.)
            filename: Current filename being processed
        """
        if stage not in self.stages:
            return
        
        metrics = self.stages[stage]
        
        # Start stage if first update
        if not metrics.start_time:
            metrics.start_time = datetime.now()
            self.current_stage = stage
        
        # Update metrics based on status
        if status == "completed":
            metrics.completed += 1
        elif status == "failed":
            metrics.failed += 1
        elif status == "skipped":
            metrics.skipped += 1
        
        # Update current file
        if filename:
            metrics.current_file = filename
        
        # Update progress bar
        if self.progress and stage in self.task_ids:
            task_id = self.task_ids[stage]
            self.progress.update(
                task_id,
                completed=metrics.completed + metrics.failed + metrics.skipped,
                description=f"{metrics.name} - {metrics.current_file}"
            )
        
        # Update live display
        if self.live:
            self.live.update(self._create_layout())
    
    async def set_stage_info(self, stage: str, info: str) -> None:
        """
        Set additional info for a stage (e.g., rate limit info).
        
        Args:
            stage: Stage name
            info: Information string
        """
        if stage in self.stages:
            self.stages[stage].rate_limit_info = info
            
            if self.live:
                self.live.update(self._create_layout())
    
    def _create_layout(self) -> Layout:
        """Create the dashboard layout."""
        layout = Layout()
        
        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="progress", size=15),
            Layout(name="metrics", size=10)
        )
        
        # Header
        layout["header"].update(
            Panel(
                f"[bold cyan]CaseMind Optimized Pipeline Dashboard[/]\n"
                f"Total Files: {self.total_files} | "
                f"Current Stage: {self.current_stage.upper()}",
                style="bold white on blue"
            )
        )
        
        # Progress bars
        layout["progress"].update(Panel(self.progress, title="Pipeline Progress"))
        
        # Metrics table
        layout["metrics"].update(self._create_metrics_table())
        
        return layout
    
    def _create_metrics_table(self) -> Table:
        """Create metrics table."""
        table = Table(title="Stage Metrics", show_header=True, header_style="bold magenta")
        
        table.add_column("Stage", style="cyan")
        table.add_column("Success", justify="right", style="green")
        table.add_column("Failed", justify="right", style="red")
        table.add_column("Skipped", justify="right", style="yellow")
        table.add_column("Rate", justify="right")
        table.add_column("Duration", justify="right")
        table.add_column("Info", style="dim")
        
        for stage_name, metrics in self.stages.items():
            duration_str = ""
            if metrics.duration:
                duration_str = str(metrics.duration).split('.')[0]  # Remove microseconds
            
            rate_str = f"{metrics.success_rate:.1f}%" if metrics.completed > 0 else "-"
            
            table.add_row(
                metrics.name,
                str(metrics.completed),
                str(metrics.failed),
                str(metrics.skipped),
                rate_str,
                duration_str,
                metrics.rate_limit_info
            )
        
        # Add overall summary
        total_completed = sum(m.completed for m in self.stages.values())
        total_failed = sum(m.failed for m in self.stages.values())
        total_skipped = sum(m.skipped for m in self.stages.values())
        overall_duration = datetime.now() - self.start_time
        
        table.add_row(
            "[bold]OVERALL[/]",
            f"[bold green]{total_completed}[/]",
            f"[bold red]{total_failed}[/]",
            f"[bold yellow]{total_skipped}[/]",
            "-",
            str(overall_duration).split('.')[0],
            ""
        )
        
        return table
    
    def print_summary(self, result) -> None:
        """
        Print final summary after pipeline completion.
        
        Args:
            result: PipelineResult
        """
        self.console.print("\n" + "=" * 70)
        self.console.print("[bold cyan]PIPELINE EXECUTION SUMMARY[/]", justify="center")
        self.console.print("=" * 70)
        
        # Overall statistics
        summary_table = Table(show_header=False, box=None)
        summary_table.add_column("Metric", style="bold")
        summary_table.add_column("Value", justify="right")
        
        summary_table.add_row("Total Files", str(result.total_files))
        summary_table.add_row(
            "✓ Successful",
            f"[green]{result.successful}[/]"
        )
        summary_table.add_row(
            "⊘ Skipped",
            f"[yellow]{result.skipped}[/]"
        )
        summary_table.add_row(
            "✗ Failed",
            f"[red]{result.failed}[/]"
        )
        summary_table.add_row(
            "Duration",
            f"{result.duration_seconds:.1f}s ({result.duration_seconds/60:.1f}m)"
        )
        summary_table.add_row(
            "Throughput",
            f"{result.total_files / (result.duration_seconds / 60):.2f} files/min"
        )
        
        self.console.print(summary_table)
        
        # Failed files details
        if result.failed_files:
            self.console.print(f"\n[bold red]Failed Files ({len(result.failed_files)}):[/]")
            
            failed_table = Table(show_header=True)
            failed_table.add_column("File", style="cyan")
            failed_table.add_column("Stage", style="yellow")
            failed_table.add_column("Error", style="red")
            
            for failed in result.failed_files[:10]:  # Show first 10
                filename = failed.get("original_filename", failed.get("file_path", "unknown"))
                stage = failed.get("stage", "unknown")
                error = failed.get("error", "unknown error")[:60]  # Truncate long errors
                
                failed_table.add_row(filename, stage, error)
            
            self.console.print(failed_table)
            
            if len(result.failed_files) > 10:
                self.console.print(f"[dim]... and {len(result.failed_files) - 10} more (see logs/failed_files.json)[/]")
        
        self.console.print("=" * 70 + "\n")


class SimpleProgressCallback:
    """Simple progress callback for pipeline monitoring."""
    
    def __init__(self, monitor: PipelineMonitor):
        """Initialize with monitor instance."""
        self.monitor = monitor
    
    async def __call__(self, stage: str, *args, **kwargs) -> None:
        """
        Progress callback.
        
        Args:
            stage: Stage name
            *args: Additional arguments
        """
        # Parse arguments based on stage
        if stage == "pdf":
            if args and hasattr(args[0], 'file_path'):
                pdf_result = args[0]
                status = "completed" if pdf_result.success else "failed"
                filename = pdf_result.file_path.name
                await self.monitor.update(stage, status, filename)
        
        elif stage == "extraction":
            # Don't show extraction progress (rate-limited, poor feedback)
            pass
        
        elif stage == "embedding":
            if args:
                filename = args[0]
                await self.monitor.update(stage, "completed", filename)
        
        elif stage == "ingestion":
            if args:
                filename = args[0]
                await self.monitor.update(stage, "completed", filename)
