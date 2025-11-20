"""
CaseMind - Legal Case Similarity Search
Main entry point for the application.
"""

import sys
import asyncio
import logging
from pathlib import Path

# Ensure src is in path
sys.path.insert(0, str(Path(__file__).parent))

from presentation.cli_app import main as cli_main
from utils.helpers import setup_logging
from core.config import Config


def main():
    """Main application entry point."""
    # Setup logging
    config = Config()
    log_level = config.get("LOG_LEVEL", "INFO")
    setup_logging(log_level)
    
    logger = logging.getLogger(__name__)
    logger.info("Starting CaseMind application")
    
    # Run CLI application
    try:
        asyncio.run(cli_main())
    except KeyboardInterrupt:
        logger.info("Application interrupted by user")
    except Exception as e:
        logger.error(f"Application error: {e}", exc_info=True)
        sys.exit(1)
    
    logger.info("CaseMind application stopped")


if __name__ == "__main__":
    main()
