"""
Health checker for monitoring component status.
"""

import asyncio
import logging
from typing import Dict, Any, List
from enum import Enum
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


class HealthStatus(str, Enum):
    """Health status enum."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class ComponentHealth:
    """Health status for a single component."""
    name: str
    status: HealthStatus
    message: str
    last_check: datetime
    details: Dict[str, Any] = None
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "status": self.status.value,
            "message": self.message,
            "last_check": self.last_check.isoformat(),
            "details": self.details or {}
        }


class HealthChecker:
    """
    Health checker for monitoring system components.
    Periodically checks health of all registered components.
    """
    
    def __init__(self, check_interval: int = 30):
        """
        Initialize health checker.
        
        Args:
            check_interval: Seconds between health checks
        """
        self.check_interval = check_interval
        self.components: Dict[str, callable] = {}
        self.health_status: Dict[str, ComponentHealth] = {}
        self._running = False
        self._task: Optional[asyncio.Task] = None
        
        logger.info(f"HealthChecker initialized (interval: {check_interval}s)")
    
    def register_component(self, name: str, check_fn: callable) -> None:
        """
        Register a component for health monitoring.
        
        Args:
            name: Component name
            check_fn: Async function that returns ComponentHealth
        """
        self.components[name] = check_fn
        logger.info(f"Registered component for health checks: {name}")
    
    async def check_health(self) -> Dict[str, ComponentHealth]:
        """
        Check health of all registered components.
        
        Returns:
            Dictionary of component health statuses
        """
        results = {}
        
        for name, check_fn in self.components.items():
            try:
                health = await check_fn()
                results[name] = health
                self.health_status[name] = health
                
                if health.status != HealthStatus.HEALTHY:
                    logger.warning(f"Component {name} is {health.status.value}: {health.message}")
                    
            except Exception as e:
                logger.error(f"Health check failed for {name}: {e}")
                results[name] = ComponentHealth(
                    name=name,
                    status=HealthStatus.UNHEALTHY,
                    message=f"Health check error: {str(e)}",
                    last_check=datetime.now()
                )
        
        return results
    
    async def start(self) -> None:
        """Start periodic health checks."""
        if self._running:
            logger.warning("HealthChecker already running")
            return
        
        self._running = True
        self._task = asyncio.create_task(self._health_check_loop())
        logger.info("✓ HealthChecker started")
    
    async def stop(self) -> None:
        """Stop health checks."""
        if not self._running:
            return
        
        self._running = False
        
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        
        logger.info("✓ HealthChecker stopped")
    
    async def _health_check_loop(self) -> None:
        """Periodic health check loop."""
        while self._running:
            try:
                await self.check_health()
                await asyncio.sleep(self.check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Health check loop error: {e}")
                await asyncio.sleep(self.check_interval)
    
    def get_overall_status(self) -> HealthStatus:
        """
        Get overall system health status.
        
        Returns:
            HEALTHY if all healthy, DEGRADED if some unhealthy, UNHEALTHY if critical components down
        """
        if not self.health_status:
            return HealthStatus.UNKNOWN
        
        statuses = [h.status for h in self.health_status.values()]
        
        if all(s == HealthStatus.HEALTHY for s in statuses):
            return HealthStatus.HEALTHY
        elif any(s == HealthStatus.UNHEALTHY for s in statuses):
            return HealthStatus.UNHEALTHY
        else:
            return HealthStatus.DEGRADED
    
    def get_health_report(self) -> dict:
        """
        Get comprehensive health report.
        
        Returns:
            Dictionary with overall status and component details
        """
        return {
            "overall_status": self.get_overall_status().value,
            "last_check": datetime.now().isoformat(),
            "components": {
                name: health.to_dict()
                for name, health in self.health_status.items()
            }
        }
