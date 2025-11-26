"""
Configuration management using Singleton pattern.
Loads configuration from environment variables and config files.
"""

import os
from pathlib import Path
from typing import Any, Dict, Optional
from dotenv import load_dotenv
import json
import logging

logger = logging.getLogger(__name__)


class Config:
    """
    Singleton configuration class.
    Loads settings from environment variables and config.json.
    """
    
    _instance: Optional['Config'] = None
    _initialized: bool = False
    
    def __new__(cls) -> 'Config':
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not self._initialized:
            self._load_config()
            Config._initialized = True
    
    def _load_config(self) -> None:
        """Load configuration from .env and config.json files."""
        # Load environment variables
        load_dotenv()
        
        # Load config.json if exists
        config_path = Path("config.json")
        if config_path.exists():
            with open(config_path, 'r', encoding='utf-8') as f:
                file_config = json.load(f)
        else:
            file_config = {}
        
        # Database configuration
        self.db_host = os.getenv('POSTGRES_HOST', 'localhost')
        self.db_port = int(os.getenv('POSTGRES_PORT', '5432'))
        self.db_name = os.getenv('POSTGRES_DB', 'casemind')
        self.db_user = os.getenv('POSTGRES_USER', 'postgres')
        self.db_password = os.getenv('POSTGRES_PASSWORD', 'password')
        
        # Connection string
        self.db_connection_string = (
            f"postgresql://{self.db_user}:{self.db_password}@"
            f"{self.db_host}:{self.db_port}/{self.db_name}"
        )
        
        # Model configuration
        self.embedding_model = os.getenv('EMBEDDING_MODEL', 'sentence-transformers/all-mpnet-base-v2')
        self.ranker_model = os.getenv('RANKER_MODEL', 'cross-encoder/ms-marco-MiniLM-L-6-v2')
        
        # Pipeline configuration
        self.top_k = int(os.getenv('TOP_K_SIMILAR_CASES', '5'))
        self.cross_encoder_threshold = float(os.getenv('CROSS_ENCODER_THRESHOLD', '0.0'))
        
        # OpenAI configuration
        self.openai_api_key = os.getenv('OPENAI_API_KEY', file_config.get('openai_api_key', ''))
        
        # Paths
        self.ontology_path = Path(os.getenv('ONTOLOGY_PATH', 'Ontology_schema/ontology_schema.json'))
        self.templates_dir = Path(os.getenv('TEMPLATES_DIR', 'templates'))
        self.cases_dir = Path(os.getenv('CASES_DIR', 'cases'))
        
        # Logging
        self.log_level = os.getenv('LOG_LEVEL', 'INFO')
        self.disable_logging = os.getenv('DISABLE_LOGGING', 'false').lower() in ('true', '1', 'yes')
        
        # Embedding dimensions
        self.embedding_dim = 768  # for all-mpnet-base-v2
        
        logger.info("Configuration loaded successfully")
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value by key."""
        return getattr(self, key, default)
    
    def to_dict(self) -> Dict[str, Any]:
        """Return configuration as dictionary (excluding sensitive data)."""
        return {
            'db_host': self.db_host,
            'db_port': self.db_port,
            'db_name': self.db_name,
            'embedding_model': self.embedding_model,
            'ranker_model': self.ranker_model,
            'top_k': self.top_k,
            'cross_encoder_threshold': self.cross_encoder_threshold,
            'embedding_dim': self.embedding_dim,
        }
