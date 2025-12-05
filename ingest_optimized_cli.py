"""
Optimized CLI for CaseMind with parallel processing support.
Run with: python ingest_optimized_cli.py --help
"""

import sys
import os
import asyncio
from pathlib import Path
import argparse
import json

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.pipelines.optimized_pipeline import create_and_run_pipeline
from src.core.lifecycle import LifecycleManager
from src.utils.logger import get_logger
from src.utils.pipeline_monitor import PipelineMonitor, SimpleProgressCallback

logger = get_logger(__name__)


async def ingest_optimized(
    file_path: str = None,
    directory: str = None,
    pattern: str = "*.pdf",
    skip_existing: bool = True,
    show_dashboard: bool = True
):
    """
    Ingest files using optimized pipeline.
    
    Args:
        file_path: Single file to ingest
        directory: Directory of files to ingest
        pattern: File pattern (default: *.pdf)
        skip_existing: Skip already ingested files
        show_dashboard: Show detailed CLI dashboard
    """
    # Collect files
    if file_path:
        files = [Path(file_path)]
    elif directory:
        files = list(Path(directory).glob(pattern))
    else:
        logger.error("Must specify --file or --directory")
        return False
    
    if not files:
        logger.error(f"No files found matching '{pattern}'")
        return False
    
    logger.info(f"\n{'='*70}")
    logger.info(f"OPTIMIZED PIPELINE - Processing {len(files)} files")
    logger.info(f"{'='*70}\n")
    
    # Create monitor
    monitor = None
    progress_callback = None
    
    if show_dashboard:
        monitor = PipelineMonitor(total_files=len(files))
        monitor.start()
        progress_callback = SimpleProgressCallback(monitor)
    
    try:
        # Run pipeline
        result = await create_and_run_pipeline(
            file_paths=files,
            skip_existing=skip_existing,
            progress_callback=progress_callback
        )
        
        # Stop monitor
        if monitor:
            monitor.stop()
            monitor.print_summary(result)
        else:
            # Print simple summary
            logger.info(f"\n{'='*70}")
            logger.info("SUMMARY")
            logger.info(f"{'='*70}")
            logger.info(f"Total Files: {result.total_files}")
            logger.info(f"Successful: {result.successful}")
            logger.info(f"Skipped: {result.skipped}")
            logger.info(f"Failed: {result.failed}")
            logger.info(f"Duration: {result.duration_seconds:.1f}s")
            logger.info(f"{'='*70}\n")
        
        return result.failed == 0
        
    except KeyboardInterrupt:
        logger.warning("\nInterrupted by user")
        if monitor:
            monitor.stop()
        return False
    
    except Exception as e:
        logger.error(f"Pipeline failed: {e}", exc_info=True)
        if monitor:
            monitor.stop()
        return False


async def health_check():
    """Check health of all pipeline components."""
    logger.info("Running health check...")
    
    lifecycle = LifecycleManager()
    
    try:
        # Initialize
        success = await lifecycle.startup()
        
        if not success:
            logger.error("❌ Health check failed: Startup unsuccessful")
            return False
        
        # Get status
        status = lifecycle.get_status()
        
        logger.info("\n" + "="*70)
        logger.info("HEALTH CHECK RESULTS")
        logger.info("="*70)
        
        logger.info(f"\nSystem State: {status['state']}")
        
        if status.get('uptime_seconds'):
            logger.info(f"Uptime: {status['uptime_seconds']:.1f}s")
        
        # Component status
        logger.info("\nComponents:")
        for component, comp_status in status.get('components', {}).items():
            logger.info(f"  {component}:")
            for key, value in comp_status.items():
                logger.info(f"    {key}: {value}")
        
        # Health details
        if 'health' in status:
            health = status['health']
            logger.info(f"\nOverall Health: {health['overall_status']}")
            
            for comp_name, comp_health in health.get('components', {}).items():
                status_emoji = "✓" if comp_health['status'] == 'healthy' else "✗"
                logger.info(f"  {status_emoji} {comp_name}: {comp_health['status']} - {comp_health['message']}")
        
        logger.info("="*70 + "\n")
        
        # Cleanup
        await lifecycle.shutdown()
        
        return True
        
    except Exception as e:
        logger.error(f"Health check failed: {e}", exc_info=True)
        return False


async def show_metrics():
    """Show performance metrics."""
    metrics_file = Path("logs/metrics.json")
    
    if not metrics_file.exists():
        logger.warning("No metrics file found")
        return
    
    with open(metrics_file, 'r') as f:
        metrics = json.load(f)
    
    logger.info("\n" + "="*70)
    logger.info("PERFORMANCE METRICS")
    logger.info("="*70)
    
    # Display metrics
    for key, value in metrics.items():
        logger.info(f"{key}: {value}")
    
    logger.info("="*70 + "\n")


def main():
    parser = argparse.ArgumentParser(
        description="CaseMind Optimized Ingestion Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Ingest single file with optimized pipeline
  python ingest_optimized_cli.py ingest --file cases/input_files/case1.pdf
  
  # Ingest directory with detailed dashboard
  python ingest_optimized_cli.py ingest --directory cases/input_files
  
  # Ingest without dashboard (faster for large batches)
  python ingest_optimized_cli.py ingest --directory cases/input_files --no-dashboard
  
  # Health check
  python ingest_optimized_cli.py health
  
  # Show metrics
  python ingest_optimized_cli.py metrics

Configuration:
  Set environment variables in .env file:
    - MAX_WORKERS: Number of parallel PDF workers (default: 3)
    - OPENAI_RPM: OpenAI rate limit in requests/minute (default: 3)
    - BATCH_SIZE_EMBEDDING: Embedding batch size (default: 100)
    - BATCH_SIZE_WEAVIATE: Weaviate batch size (default: 200)
    
  See .env.example for full configuration options.
        """
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    
    # Ingest command
    ingest_parser = subparsers.add_parser("ingest", help="Ingest files using optimized pipeline")
    ingest_group = ingest_parser.add_mutually_exclusive_group(required=True)
    ingest_group.add_argument("--file", help="Single file to ingest")
    ingest_group.add_argument("--directory", help="Directory of files to ingest")
    ingest_parser.add_argument("--pattern", default="*.pdf", help="File pattern (default: *.pdf)")
    ingest_parser.add_argument("--allow-duplicates", action="store_true",
                              help="Allow re-ingestion of existing files")
    ingest_parser.add_argument("--no-dashboard", action="store_true",
                              help="Disable detailed CLI dashboard")
    
    # Health command
    health_parser = subparsers.add_parser("health", help="Check health of pipeline components")
    
    # Metrics command
    metrics_parser = subparsers.add_parser("metrics", help="Show performance metrics")
    
    args = parser.parse_args()
    
    if args.command == "ingest":
        success = asyncio.run(ingest_optimized(
            file_path=args.file,
            directory=args.directory,
            pattern=args.pattern,
            skip_existing=not args.allow_duplicates,
            show_dashboard=not args.no_dashboard
        ))
        sys.exit(0 if success else 1)
    
    elif args.command == "health":
        success = asyncio.run(health_check())
        sys.exit(0 if success else 1)
    
    elif args.command == "metrics":
        asyncio.run(show_metrics())
        sys.exit(0)
    
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
