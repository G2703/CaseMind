"""
Failure Tracker for CaseMind Ingestion Pipeline.
Tracks failed files with retry attempts and manages failure history.
"""

import json
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
from dataclasses import dataclass, asdict


@dataclass
class FailureRecord:
    """Record of a failed file ingestion."""
    file_path: str
    file_hash: str
    attempts: int
    max_attempts: int
    last_failure: str
    stage: str
    error: str
    original_filename: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'FailureRecord':
        """Create from dictionary."""
        return cls(**data)


class FailureTracker:
    """
    Tracks failed file ingestions and manages retry attempts.
    
    Features:
    - Tracks up to max_attempts (default: 3) per file
    - Stores failure stage and error message
    - Clears records after successful retry
    - Persistent storage in JSON file
    """
    
    def __init__(self, tracking_file: Path = None, max_attempts: int = 3):
        """
        Initialize failure tracker.
        
        Args:
            tracking_file: Path to failure tracking JSON file (default: logs/failed_files.json)
            max_attempts: Maximum retry attempts per file (default: 3)
        """
        if tracking_file is None:
            tracking_file = Path("logs/failed_files.json")
        
        self.tracking_file = Path(tracking_file)
        self.max_attempts = max_attempts
        self.failures: Dict[str, FailureRecord] = {}
        
        # Ensure logs directory exists
        self.tracking_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Load existing failures
        self._load()
    
    def _load(self):
        """Load failures from tracking file."""
        if not self.tracking_file.exists():
            return
        
        try:
            with open(self.tracking_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                failures_data = data.get('failures', {})
                
                for key, record_data in failures_data.items():
                    self.failures[key] = FailureRecord.from_dict(record_data)
        
        except Exception as e:
            print(f"Warning: Failed to load failure tracking file: {e}")
    
    def _save(self):
        """Save failures to tracking file."""
        try:
            data = {
                'failures': {
                    key: record.to_dict() 
                    for key, record in self.failures.items()
                }
            }
            
            with open(self.tracking_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        
        except Exception as e:
            print(f"Warning: Failed to save failure tracking file: {e}")
    
    def _compute_file_hash(self, file_path: Path) -> str:
        """Compute SHA-256 hash of file."""
        sha256 = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                sha256.update(chunk)
        return sha256.hexdigest()
    
    def record_failure(
        self, 
        file_path: Path, 
        stage: str, 
        error: str
    ) -> bool:
        """
        Record a file failure.
        
        Args:
            file_path: Path to the failed file
            stage: Pipeline stage where failure occurred
            error: Error message
            
        Returns:
            True if file should be retried, False if max attempts reached
        """
        file_path = Path(file_path)
        
        try:
            file_hash = self._compute_file_hash(file_path)
        except Exception as e:
            print(f"Warning: Could not compute file hash: {e}")
            file_hash = "unknown"
        
        key = str(file_path)
        
        if key in self.failures:
            # Update existing record
            record = self.failures[key]
            record.attempts += 1
            record.last_failure = datetime.now().isoformat()
            record.stage = stage
            record.error = error
        else:
            # Create new record
            record = FailureRecord(
                file_path=str(file_path),
                file_hash=file_hash,
                attempts=1,
                max_attempts=self.max_attempts,
                last_failure=datetime.now().isoformat(),
                stage=stage,
                error=error,
                original_filename=file_path.name
            )
            self.failures[key] = record
        
        self._save()
        
        # Return True if should retry, False if max attempts reached
        return record.attempts < self.max_attempts
    
    def record_success(self, file_path: Path):
        """
        Record successful ingestion (clears failure record).
        
        Args:
            file_path: Path to the successfully ingested file
        """
        key = str(Path(file_path))
        
        if key in self.failures:
            del self.failures[key]
            self._save()
    
    def get_failed_files(self, directory: Optional[Path] = None) -> List[FailureRecord]:
        """
        Get list of failed files.
        
        Args:
            directory: Optional directory to filter by
            
        Returns:
            List of FailureRecord objects
        """
        failed = list(self.failures.values())
        
        if directory:
            directory = Path(directory).resolve()
            failed = [
                f for f in failed 
                if Path(f.file_path).resolve().parent == directory
            ]
        
        return failed
    
    def get_retryable_files(self, directory: Optional[Path] = None) -> List[Path]:
        """
        Get list of files that should be retried (haven't reached max attempts).
        
        Args:
            directory: Optional directory to filter by
            
        Returns:
            List of file paths
        """
        failed = self.get_failed_files(directory)
        retryable = [
            Path(f.file_path) 
            for f in failed 
            if f.attempts < self.max_attempts
        ]
        return retryable
    
    def should_retry(self, file_path: Path) -> bool:
        """
        Check if a file should be retried.
        
        Args:
            file_path: Path to check
            
        Returns:
            True if file should be retried, False otherwise
        """
        key = str(Path(file_path))
        
        if key not in self.failures:
            return True  # Not in failures, can try
        
        record = self.failures[key]
        return record.attempts < self.max_attempts
    
    def get_attempt_count(self, file_path: Path) -> int:
        """
        Get number of attempts for a file.
        
        Args:
            file_path: Path to check
            
        Returns:
            Number of attempts (0 if not in failures)
        """
        key = str(Path(file_path))
        
        if key not in self.failures:
            return 0
        
        return self.failures[key].attempts
    
    def clear_all(self):
        """Clear all failure records."""
        self.failures = {}
        self._save()
    
    def get_summary(self) -> Dict[str, Any]:
        """
        Get summary statistics of failures.
        
        Returns:
            Dictionary with failure statistics
        """
        if not self.failures:
            return {
                'total_failures': 0,
                'retryable': 0,
                'max_attempts_reached': 0,
                'stages': {}
            }
        
        retryable = sum(1 for f in self.failures.values() if f.attempts < self.max_attempts)
        max_reached = sum(1 for f in self.failures.values() if f.attempts >= self.max_attempts)
        
        # Count by stage
        stages = {}
        for record in self.failures.values():
            stage = record.stage
            stages[stage] = stages.get(stage, 0) + 1
        
        return {
            'total_failures': len(self.failures),
            'retryable': retryable,
            'max_attempts_reached': max_reached,
            'stages': stages
        }
