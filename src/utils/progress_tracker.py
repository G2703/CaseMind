"""
Progress Tracker for CaseMind Ingestion Pipeline.
Provides tqdm-based progress bars for single file and batch processing.
"""

from typing import Optional
from pathlib import Path
from tqdm import tqdm


class ProgressTracker:
    """
    Manages progress bars for ingestion pipeline.
    
    Features:
    - Single file: Shows pipeline stages (7 stages)
    - Batch processing: Outer bar for files, inner bar for stages
    """
    
    # Pipeline stages
    STAGES = [
        "PDF Conversion",
        "Markdown Normalization",
        "Text Chunking",
        "Summary Extraction",
        "Template Facts Extraction",
        "Embedding Generation",
        "Weaviate Writing"
    ]
    
    def __init__(self, total_files: int = 1, disable: bool = False):
        """
        Initialize progress tracker.
        
        Args:
            total_files: Total number of files to process
            disable: Disable progress bars (useful for testing)
        """
        self.total_files = total_files
        self.disable = disable
        self.file_bar = None
        self.stage_bar = None
        self.current_file = 0
    
    def start_batch(self, description: str = "Processing files"):
        """Start batch progress bar."""
        if self.total_files > 1 and not self.disable:
            self.file_bar = tqdm(
                total=self.total_files,
                desc=description,
                unit="file",
                position=0,
                leave=True,
                bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]'
            )
    
    def start_file(self, filename: str):
        """Start progress for a single file."""
        self.current_file += 1
        
        if not self.disable:
            # Update file bar description if in batch mode
            if self.file_bar:
                self.file_bar.set_description(f"Processing {filename}")
            
            # Create stage progress bar
            position = 1 if self.file_bar else 0
            self.stage_bar = tqdm(
                total=len(self.STAGES),
                desc="Pipeline stages",
                unit="stage",
                position=position,
                leave=False,
                bar_format='{desc}: {percentage:3.0f}%|{bar}| {n_fmt}/{total_fmt}'
            )
    
    def update_stage(self, stage_index: int):
        """
        Update progress to a specific stage.
        
        Args:
            stage_index: Index of the current stage (0-6)
        """
        if self.stage_bar and not self.disable:
            current = self.stage_bar.n
            advance = stage_index - current
            if advance > 0:
                self.stage_bar.update(advance)
                if stage_index < len(self.STAGES):
                    self.stage_bar.set_description(f"Stage: {self.STAGES[stage_index]}")
    
    def complete_stage(self, stage_name: str):
        """
        Mark a stage as complete.
        
        Args:
            stage_name: Name of the completed stage
        """
        if self.stage_bar and not self.disable:
            try:
                stage_index = next(i for i, s in enumerate(self.STAGES) if stage_name.lower() in s.lower())
                self.update_stage(stage_index + 1)
            except StopIteration:
                # Stage name not found, just increment
                self.stage_bar.update(1)
    
    def complete_file(self):
        """Mark current file as complete."""
        if not self.disable:
            # Complete stage bar
            if self.stage_bar:
                self.stage_bar.update(self.stage_bar.total - self.stage_bar.n)
                self.stage_bar.close()
                self.stage_bar = None
            
            # Update file bar
            if self.file_bar:
                self.file_bar.update(1)
    
    def fail_file(self, error: str = ""):
        """Mark current file as failed."""
        if not self.disable:
            # Close stage bar
            if self.stage_bar:
                self.stage_bar.close()
                self.stage_bar = None
            
            # Update file bar
            if self.file_bar:
                self.file_bar.update(1)
    
    def close(self):
        """Close all progress bars."""
        if self.stage_bar:
            self.stage_bar.close()
            self.stage_bar = None
        
        if self.file_bar:
            self.file_bar.close()
            self.file_bar = None
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()


class SingleFileProgressTracker:
    """Simplified progress tracker for single file processing."""
    
    def __init__(self, filename: str, disable: bool = False):
        """
        Initialize single file progress tracker.
        
        Args:
            filename: Name of the file being processed
            disable: Disable progress bar
        """
        self.filename = filename
        self.disable = disable
        self.progress_bar = None
        
        if not disable:
            self.progress_bar = tqdm(
                total=len(ProgressTracker.STAGES),
                desc=f"Processing {filename}",
                unit="stage",
                bar_format='{desc}: {percentage:3.0f}%|{bar}| {n_fmt}/{total_fmt} stages'
            )
    
    def update(self, stage_name: str):
        """Update progress."""
        if self.progress_bar:
            try:
                stage_index = next(
                    i for i, s in enumerate(ProgressTracker.STAGES) 
                    if stage_name.lower() in s.lower()
                )
                self.progress_bar.n = stage_index + 1
                self.progress_bar.set_description(f"{self.filename} - {stage_name}")
                self.progress_bar.refresh()
            except StopIteration:
                self.progress_bar.update(1)
    
    def complete(self):
        """Mark as complete."""
        if self.progress_bar:
            self.progress_bar.update(self.progress_bar.total - self.progress_bar.n)
            self.progress_bar.close()
    
    def close(self):
        """Close progress bar."""
        if self.progress_bar:
            self.progress_bar.close()
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
