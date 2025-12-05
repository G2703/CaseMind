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
        
        # Weaviate Configuration
        self.weaviate_url = os.getenv('WEAVIATE_URL', 'http://localhost:8080')
        self.weaviate_grpc_host = os.getenv('WEAVIATE_GRPC_HOST', 'localhost')
        self.weaviate_grpc_port = int(os.getenv('WEAVIATE_GRPC_PORT', '50051'))
        self.weaviate_timeout = int(os.getenv('WEAVIATE_TIMEOUT', '60'))
        
        # Local Storage Configuration
        self.local_storage_path = Path(os.getenv('LOCAL_STORAGE_PATH', 'cases/local_storage_md'))
        
        # Chunking Configuration
        self.chunk_size_tokens = int(os.getenv('CHUNK_SIZE_TOKENS', '300'))
        self.chunk_overlap_tokens = int(os.getenv('CHUNK_OVERLAP_TOKENS', '30'))
        
        # Model configuration
        self.embedding_model = os.getenv('EMBEDDING_MODEL', 'sentence-transformers/all-mpnet-base-v2')
        self.ranker_model = os.getenv('RANKER_MODEL', 'cross-encoder/ms-marco-MiniLM-L-6-v2')
        
        # Pipeline configuration
        self.top_k = int(os.getenv('TOP_K_SIMILAR_CASES', '5'))
        self.cross_encoder_threshold = float(os.getenv('CROSS_ENCODER_THRESHOLD', '0.0'))
        
        # Hybrid search weights
        self.hybrid_search_alpha = float(os.getenv('HYBRID_SEARCH_ALPHA', '0.7'))
        self.hybrid_search_beta = float(os.getenv('HYBRID_SEARCH_BETA', '0.3'))
        
        # OpenAI configuration
        self.openai_api_key = os.getenv('OPENAI_API_KEY', file_config.get('openai_api_key', ''))
        
        # Gemini configuration
        self.gemini_api_key = os.getenv('GEMINI_API_KEY', file_config.get('gemini_api_key', ''))
        
        # Paths
        self.ontology_path = Path(os.getenv('ONTOLOGY_PATH', 'Ontology_schema/ontology_schema.json'))
        self.templates_dir = Path(os.getenv('TEMPLATES_DIR', 'templates'))
        self.cases_dir = Path(os.getenv('CASES_DIR', 'cases'))
        
        # Templates and Prompts
        self.main_template_path = Path(os.getenv('MAIN_TEMPLATE_PATH', 'templates/main_template.json'))
        self.prompts_path = Path(os.getenv('PROMPTS_PATH', 'prompts/prompts.json'))
        self.fact_templates_path = Path(os.getenv('FACT_TEMPLATES_PATH', 'templates/templates.json'))
        
        # Logging
        self.log_level = os.getenv('LOG_LEVEL', 'INFO')
        self.log_file = os.getenv('LOG_FILE', 'logs/casemind.log')
        self.disable_logging = os.getenv('DISABLE_LOGGING', 'false').lower() in ('true', '1', 'yes')
        
        # Embedding dimensions
        self.embedding_dim = 768  # for all-mpnet-base-v2
        
        # Parallel Processing Configuration
        self.max_workers = int(os.getenv('MAX_WORKERS', '3'))
        self.worker_queue_size = int(os.getenv('WORKER_QUEUE_SIZE', '100'))
        
        # Batch Processing Configuration
        self.batch_size_pdf = int(os.getenv('BATCH_SIZE_PDF', '10'))
        self.batch_size_embedding = int(os.getenv('BATCH_SIZE_EMBEDDING', '100'))
        self.batch_size_weaviate = int(os.getenv('BATCH_SIZE_WEAVIATE', '200'))
        
        # API Rate Limiting
        self.openai_rpm = int(os.getenv('OPENAI_RPM', '3'))
        self.openai_max_retries = int(os.getenv('OPENAI_MAX_RETRIES', '3'))
        self.openai_retry_delay = int(os.getenv('OPENAI_RETRY_DELAY', '2'))
        
        # Resource Management
        self.weaviate_pool_size = int(os.getenv('WEAVIATE_POOL_SIZE', '3'))
        self.embedding_warmup = os.getenv('EMBEDDING_WARMUP', 'true').lower() == 'true'
        self.keep_alive = os.getenv('KEEP_ALIVE', 'true').lower() == 'true'
        
        # Lifecycle Configuration
        self.startup_timeout = int(os.getenv('STARTUP_TIMEOUT', '120'))
        self.shutdown_grace_period = int(os.getenv('SHUTDOWN_GRACE_PERIOD', '30'))
        self.health_check_interval = int(os.getenv('HEALTH_CHECK_INTERVAL', '30'))
        
        # Error Handling
        self.auto_retry_failed = os.getenv('AUTO_RETRY_FAILED', 'true').lower() == 'true'
        self.save_failed_files = os.getenv('SAVE_FAILED_FILES', 'true').lower() == 'true'
        self.continue_on_error = os.getenv('CONTINUE_ON_ERROR', 'true').lower() == 'true'
        
        # Performance Monitoring
        self.enable_metrics = os.getenv('ENABLE_METRICS', 'true').lower() == 'true'
        self.metrics_output = Path(os.getenv('METRICS_OUTPUT', 'logs/metrics.json'))
        self.show_dashboard = os.getenv('SHOW_DASHBOARD', 'true').lower() == 'true'
        
        logger.info("Configuration loaded successfully")
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value by key."""
        return getattr(self, key, default)
    
    def to_dict(self) -> Dict[str, Any]:
        """Return configuration as dictionary (excluding sensitive data)."""
        return {
            'weaviate_url': self.weaviate_url,
            'weaviate_grpc_port': self.weaviate_grpc_port,
            'local_storage_path': str(self.local_storage_path),
            'chunk_size_tokens': self.chunk_size_tokens,
            'chunk_overlap_tokens': self.chunk_overlap_tokens,
            'embedding_model': self.embedding_model,
            'ranker_model': self.ranker_model,
            'top_k': self.top_k,
            'cross_encoder_threshold': self.cross_encoder_threshold,
            'hybrid_search_alpha': self.hybrid_search_alpha,
            'hybrid_search_beta': self.hybrid_search_beta,
            'embedding_dim': self.embedding_dim,
        }
