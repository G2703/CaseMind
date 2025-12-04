"""
Report Generator for CaseMind Ingestion Pipeline.
Generates JSON and human-readable text reports for ingestion runs.
"""

import json
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime
from dataclasses import dataclass, asdict


@dataclass
class IngestionResult:
    """Result of a single file ingestion."""
    file_id: str
    original_filename: str
    status: str  # 'success', 'skipped', 'error'
    message: str
    stage: str = ""
    error_details: Dict[str, Any] = None
    sections_count: int = 0
    chunks_count: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


class ReportGenerator:
    """
    Generates ingestion reports in multiple formats.
    
    Formats:
    - JSON: Machine-readable format
    - TXT: Human-readable summary
    """
    
    def __init__(self, output_dir: Path = None):
        """
        Initialize report generator.
        
        Args:
            output_dir: Directory to save reports (default: logs/)
        """
        if output_dir is None:
            output_dir = Path("logs")
        
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def generate_report(
        self,
        results: List[Dict[str, Any]],
        directory: str = "",
        save: bool = True
    ) -> Dict[str, Any]:
        """
        Generate ingestion report from results.
        
        Args:
            results: List of ingestion results from WeaviateWriter
            directory: Directory that was processed
            save: Whether to save report to files
            
        Returns:
            Report dictionary with statistics
        """
        timestamp = datetime.now()
        
        # Count statistics
        successful = [r for r in results if r.get('status') == 'success']
        duplicates = [r for r in results if r.get('status') == 'skipped']
        failed = [r for r in results if r.get('status') == 'error']
        
        # Build report
        report = {
            'run_timestamp': timestamp.isoformat(),
            'directory': directory,
            'total_files': len(results),
            'successful': len(successful),
            'duplicates': len(duplicates),
            'failed': len(failed),
            'failed_files': [
                {
                    'filename': f.get('original_filename', 'unknown'),
                    'file_id': f.get('file_id', ''),
                    'stage': f.get('error_details', {}).get('stage', 'unknown') if f.get('error_details') else 'unknown',
                    'error': f.get('message', 'Unknown error')
                }
                for f in failed
            ],
            'duplicate_files': [
                {
                    'filename': f.get('original_filename', 'unknown'),
                    'file_id': f.get('file_id', '')
                }
                for f in duplicates
            ],
            'successful_files': [
                {
                    'filename': f.get('original_filename', 'unknown'),
                    'file_id': f.get('file_id', ''),
                    'sections': f.get('sections_count', 0),
                    'chunks': f.get('chunks_count', 0)
                }
                for f in successful
            ]
        }
        
        if save:
            self._save_json_report(report, timestamp)
            self._save_text_report(report, timestamp)
        
        return report
    
    def _save_json_report(self, report: Dict[str, Any], timestamp: datetime):
        """Save JSON report."""
        filename = f"ingestion_report_{timestamp.strftime('%Y%m%d_%H%M%S')}.json"
        filepath = self.output_dir / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        print(f"\n📄 JSON report saved: {filepath}")
    
    def _save_text_report(self, report: Dict[str, Any], timestamp: datetime):
        """Save human-readable text report."""
        filename = f"ingestion_report_{timestamp.strftime('%Y%m%d_%H%M%S')}.txt"
        filepath = self.output_dir / filename
        
        lines = []
        lines.append("=" * 80)
        lines.append("CASEMIND INGESTION REPORT")
        lines.append("=" * 80)
        lines.append(f"Run Time: {timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"Directory: {report['directory']}")
        lines.append("")
        
        # Summary
        lines.append("-" * 80)
        lines.append("SUMMARY")
        lines.append("-" * 80)
        lines.append(f"Total Files Processed: {report['total_files']}")
        lines.append(f"  ✓ Successful:        {report['successful']}")
        lines.append(f"  ⊘ Duplicates:        {report['duplicates']}")
        lines.append(f"  ✗ Failed:            {report['failed']}")
        lines.append("")
        
        # Successful files
        if report['successful'] > 0:
            lines.append("-" * 80)
            lines.append(f"SUCCESSFUL FILES ({report['successful']})")
            lines.append("-" * 80)
            for item in report['successful_files']:
                lines.append(f"✓ {item['filename']}")
                lines.append(f"  File ID: {item['file_id']}")
                lines.append(f"  Sections: {item['sections']}, Chunks: {item['chunks']}")
                lines.append("")
        
        # Duplicate files
        if report['duplicates'] > 0:
            lines.append("-" * 80)
            lines.append(f"DUPLICATE FILES (SKIPPED) ({report['duplicates']})")
            lines.append("-" * 80)
            for item in report['duplicate_files']:
                lines.append(f"⊘ {item['filename']}")
                lines.append(f"  File ID: {item['file_id']}")
                lines.append("")
        
        # Failed files
        if report['failed'] > 0:
            lines.append("-" * 80)
            lines.append(f"FAILED FILES ({report['failed']})")
            lines.append("-" * 80)
            
            # Group by stage
            by_stage = {}
            for item in report['failed_files']:
                stage = item['stage']
                if stage not in by_stage:
                    by_stage[stage] = []
                by_stage[stage].append(item)
            
            for stage, items in by_stage.items():
                lines.append(f"\nStage: {stage} ({len(items)} files)")
                lines.append("-" * 40)
                for item in items:
                    lines.append(f"✗ {item['filename']}")
                    lines.append(f"  Error: {item['error']}")
                    lines.append("")
        
        lines.append("=" * 80)
        lines.append("END OF REPORT")
        lines.append("=" * 80)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))
        
        print(f"📄 Text report saved: {filepath}")
    
    def print_summary(self, report: Dict[str, Any]):
        """Print summary to console."""
        print("\n" + "=" * 80)
        print("INGESTION SUMMARY")
        print("=" * 80)
        print(f"Total Files:  {report['total_files']}")
        print(f"  ✓ Success:  {report['successful']}")
        print(f"  ⊘ Skipped:  {report['duplicates']}")
        print(f"  ✗ Failed:   {report['failed']}")
        
        if report['failed'] > 0:
            print("\n" + "-" * 80)
            print("FAILED FILES:")
            print("-" * 80)
            for item in report['failed_files']:
                print(f"  ✗ {item['filename']}")
                print(f"    Stage: {item['stage']}")
                print(f"    Error: {item['error']}")
        
        print("=" * 80 + "\n")
