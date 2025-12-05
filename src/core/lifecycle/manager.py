"""
Lifecycle Manager - Central coordinator for system lifecycle.
Manages startup, shutdown, and health monitoring of all components.
"""

import asyncio
import logging
from typing import Optional, Dict, Any
from enum import Enum
from datetime import datetime

from src.core.config import Config
from src.core.pools import WeaviateConnectionPool, EmbeddingModelPool, OpenAIClientPool
from src.core.lifecycle.health_checker import HealthChecker, HealthStatus, ComponentHealth

logger = logging.getLogger(__name__)


class LifecycleState(str, Enum):
    """Lifecycle states."""
    INITIALIZING = "initializing"
    STARTING = "starting"
    READY = "ready"
    SHUTTING_DOWN = "shutting_down"
    STOPPED = "stopped"
    ERROR = "error"


class LifecycleManager:
    """
    Central lifecycle manager for CaseMind pipeline.
    Manages initialization, health monitoring, and graceful shutdown.
    """
    
    _instance: Optional['LifecycleManager'] = None
    
    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self, config: Optional[Config] = None):
        """
        Initialize lifecycle manager.
        
        Args:
            config: Configuration instance
        """
        # Only initialize once
        if hasattr(self, '_initialized') and self._initialized:
            return
        
        self.config = config or Config()
        self.state = LifecycleState.INITIALIZING
        self._initialized = False
        self._startup_time: Optional[datetime] = None
        
        # Resource pools
        self.weaviate_pool: Optional[WeaviateConnectionPool] = None
        self.embedding_pool: Optional[EmbeddingModelPool] = None
        self.openai_pool: Optional[OpenAIClientPool] = None
        
        # Health monitoring
        self.health_checker: Optional[HealthChecker] = None
        
        logger.info("=" * 70)
        logger.info("LifecycleManager initializing...")
        logger.info("=" * 70)
    
    async def startup(self) -> bool:
        """
        Start all system components.
        
        Returns:
            True if startup successful, False otherwise
        """
        if self.state != LifecycleState.INITIALIZING:
            logger.warning(f"Cannot start from state: {self.state}")
            return False
        
        self.state = LifecycleState.STARTING
        self._startup_time = datetime.now()
        
        try:
            logger.info("\n🚀 Starting CaseMind Pipeline...")
            
            # Step 1: Initialize Weaviate connection pool
            logger.info("\n[1/4] Initializing Weaviate connection pool...")
            pool_size = int(os.getenv('WEAVIATE_POOL_SIZE', '3'))
            self.weaviate_pool = WeaviateConnectionPool(pool_size=pool_size, config=self.config)
            await self.weaviate_pool.initialize()
            logger.info(f"✓ Weaviate pool ready ({pool_size} connections)")
            
            # Step 2: Initialize embedding model pool
            if os.getenv('EMBEDDING_WARMUP', 'true').lower() == 'true':
                logger.info("\n[2/4] Loading embedding model (this may take a moment)...")
                self.embedding_pool = EmbeddingModelPool(config=self.config)
                await self.embedding_pool.initialize()
                logger.info(f"✓ Embedding model ready ({self.embedding_pool.model_name})")
            else:
                logger.info("\n[2/4] Skipping embedding model warmup (lazy loading enabled)")
                self.embedding_pool = EmbeddingModelPool(config=self.config)
            
            # Step 3: Initialize OpenAI client pool
            logger.info("\n[3/4] Initializing OpenAI client...")
            rpm = int(os.getenv('OPENAI_RPM', '3'))
            self.openai_pool = OpenAIClientPool(rpm=rpm, config=self.config)
            await self.openai_pool.initialize()
            logger.info(f"✓ OpenAI client ready ({rpm} RPM limit)")
            
            # Step 4: Start health monitoring
            if os.getenv('HEALTH_CHECK_INTERVAL'):
                logger.info("\n[4/4] Starting health monitoring...")
                interval = int(os.getenv('HEALTH_CHECK_INTERVAL', '30'))
                self.health_checker = HealthChecker(check_interval=interval)
                
                # Register components for health checks
                self.health_checker.register_component(
                    "weaviate_pool",
                    self._check_weaviate_health
                )
                self.health_checker.register_component(
                    "embedding_pool",
                    self._check_embedding_health
                )
                self.health_checker.register_component(
                    "openai_pool",
                    self._check_openai_health
                )
                
                await self.health_checker.start()
                logger.info(f"✓ Health checker active (interval: {interval}s)")
            else:
                logger.info("\n[4/4] Health monitoring disabled")
            
            # Startup complete
            self.state = LifecycleState.READY
            self._initialized = True
            
            startup_duration = (datetime.now() - self._startup_time).total_seconds()
            
            logger.info("\n" + "=" * 70)
            logger.info(f"✅ System READY (startup time: {startup_duration:.2f}s)")
            logger.info("=" * 70 + "\n")
            
            return True
            
        except Exception as e:
            logger.error(f"\n❌ Startup failed: {e}", exc_info=True)
            self.state = LifecycleState.ERROR
            await self.shutdown()
            return False
    
    async def shutdown(self) -> None:
        """Gracefully shutdown all components."""
        if self.state == LifecycleState.STOPPED:
            logger.info("System already stopped")
            return
        
        logger.info("\n" + "=" * 70)
        logger.info("🛑 Shutting down CaseMind Pipeline...")
        logger.info("=" * 70)
        
        self.state = LifecycleState.SHUTTING_DOWN
        
        grace_period = int(os.getenv('SHUTDOWN_GRACE_PERIOD', '30'))
        logger.info(f"Grace period: {grace_period}s")
        
        # Stop health checker
        if self.health_checker:
            logger.info("\n[1/4] Stopping health checker...")
            await self.health_checker.stop()
            logger.info("✓ Health checker stopped")
        
        # Close OpenAI pool
        if self.openai_pool:
            logger.info("\n[2/4] Closing OpenAI client...")
            await self.openai_pool.close()
            logger.info("✓ OpenAI client closed")
        
        # Close embedding pool
        if self.embedding_pool:
            logger.info("\n[3/4] Unloading embedding model...")
            await self.embedding_pool.close()
            logger.info("✓ Embedding model unloaded")
        
        # Close Weaviate pool
        if self.weaviate_pool:
            logger.info("\n[4/4] Closing Weaviate connections...")
            await self.weaviate_pool.close()
            logger.info("✓ Weaviate connections closed")
        
        self.state = LifecycleState.STOPPED
        
        logger.info("\n" + "=" * 70)
        logger.info("✅ Shutdown complete")
        logger.info("=" * 70 + "\n")
    
    async def _check_weaviate_health(self) -> ComponentHealth:
        """Check Weaviate pool health."""
        try:
            if not self.weaviate_pool or not self.weaviate_pool._initialized:
                return ComponentHealth(
                    name="weaviate_pool",
                    status=HealthStatus.UNHEALTHY,
                    message="Pool not initialized",
                    last_check=datetime.now()
                )
            
            status = self.weaviate_pool.get_status()
            
            return ComponentHealth(
                name="weaviate_pool",
                status=HealthStatus.HEALTHY,
                message="All connections healthy",
                last_check=datetime.now(),
                details=status
            )
            
        except Exception as e:
            return ComponentHealth(
                name="weaviate_pool",
                status=HealthStatus.UNHEALTHY,
                message=str(e),
                last_check=datetime.now()
            )
    
    async def _check_embedding_health(self) -> ComponentHealth:
        """Check embedding pool health."""
        try:
            if not self.embedding_pool:
                return ComponentHealth(
                    name="embedding_pool",
                    status=HealthStatus.UNKNOWN,
                    message="Pool not created (lazy loading)",
                    last_check=datetime.now()
                )
            
            status = self.embedding_pool.get_status()
            
            if status["initialized"] and status["model_loaded"]:
                return ComponentHealth(
                    name="embedding_pool",
                    status=HealthStatus.HEALTHY,
                    message="Model loaded and ready",
                    last_check=datetime.now(),
                    details=status
                )
            else:
                return ComponentHealth(
                    name="embedding_pool",
                    status=HealthStatus.DEGRADED,
                    message="Model not loaded (will load on first use)",
                    last_check=datetime.now(),
                    details=status
                )
            
        except Exception as e:
            return ComponentHealth(
                name="embedding_pool",
                status=HealthStatus.UNHEALTHY,
                message=str(e),
                last_check=datetime.now()
            )
    
    async def _check_openai_health(self) -> ComponentHealth:
        """Check OpenAI pool health."""
        try:
            if not self.openai_pool or not self.openai_pool._initialized:
                return ComponentHealth(
                    name="openai_pool",
                    status=HealthStatus.UNHEALTHY,
                    message="Client not initialized",
                    last_check=datetime.now()
                )
            
            status = self.openai_pool.get_status()
            
            return ComponentHealth(
                name="openai_pool",
                status=HealthStatus.HEALTHY,
                message="Client ready",
                last_check=datetime.now(),
                details=status
            )
            
        except Exception as e:
            return ComponentHealth(
                name="openai_pool",
                status=HealthStatus.UNHEALTHY,
                message=str(e),
                last_check=datetime.now()
            )
    
    def get_status(self) -> dict:
        """Get overall system status."""
        status = {
            "state": self.state.value,
            "uptime_seconds": None,
            "components": {}
        }
        
        if self._startup_time:
            uptime = (datetime.now() - self._startup_time).total_seconds()
            status["uptime_seconds"] = uptime
        
        if self.weaviate_pool:
            status["components"]["weaviate_pool"] = self.weaviate_pool.get_status()
        
        if self.embedding_pool:
            status["components"]["embedding_pool"] = self.embedding_pool.get_status()
        
        if self.openai_pool:
            status["components"]["openai_pool"] = self.openai_pool.get_status()
        
        if self.health_checker:
            status["health"] = self.health_checker.get_health_report()
        
        return status


import os
