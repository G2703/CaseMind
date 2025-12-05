"""
Token Bucket Rate Limiter for API calls.
Ensures we don't exceed API rate limits (e.g., OpenAI 3 RPM).
"""

import asyncio
import time
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class RateLimiter:
    """
    Token bucket rate limiter for controlling request rates.
    
    Example:
        limiter = RateLimiter(requests_per_minute=3)
        async with limiter:
            # Make API call
            response = await api_call()
    """
    
    def __init__(
        self,
        requests_per_minute: int,
        burst_size: Optional[int] = None
    ):
        """
        Initialize rate limiter.
        
        Args:
            requests_per_minute: Maximum requests per minute
            burst_size: Maximum burst size (defaults to requests_per_minute)
        """
        self.rpm = requests_per_minute
        self.tokens = float(requests_per_minute)
        self.max_tokens = float(burst_size or requests_per_minute)
        self.refill_rate = requests_per_minute / 60.0  # tokens per second
        self.last_refill = time.monotonic()
        self.lock = asyncio.Lock()
        
        logger.info(f"RateLimiter initialized: {self.rpm} RPM (max burst: {self.max_tokens})")
    
    async def _refill_tokens(self) -> None:
        """Refill tokens based on elapsed time."""
        now = time.monotonic()
        elapsed = now - self.last_refill
        
        # Add tokens based on elapsed time
        tokens_to_add = elapsed * self.refill_rate
        self.tokens = min(self.max_tokens, self.tokens + tokens_to_add)
        self.last_refill = now
        
        logger.debug(f"Refilled tokens: {self.tokens:.2f}/{self.max_tokens}")
    
    async def acquire(self) -> None:
        """
        Acquire a token (wait if necessary).
        Blocks until a token is available.
        """
        async with self.lock:
            while True:
                await self._refill_tokens()
                
                if self.tokens >= 1.0:
                    self.tokens -= 1.0
                    logger.debug(f"Token acquired. Remaining: {self.tokens:.2f}")
                    return
                
                # Calculate wait time for next token
                wait_time = (1.0 - self.tokens) / self.refill_rate
                logger.debug(f"Rate limit reached. Waiting {wait_time:.2f}s for next token")
                
                await asyncio.sleep(wait_time)
    
    async def __aenter__(self):
        """Context manager entry - acquire token."""
        await self.acquire()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        pass
    
    def get_status(self) -> dict:
        """Get current rate limiter status."""
        return {
            "rpm": self.rpm,
            "tokens_available": self.tokens,
            "max_tokens": self.max_tokens,
            "refill_rate_per_sec": self.refill_rate
        }


class MultiRateLimiter:
    """
    Manage multiple rate limiters (e.g., per-minute and per-day limits).
    All limiters must allow before proceeding.
    """
    
    def __init__(self, limiters: list[RateLimiter]):
        """Initialize with multiple rate limiters."""
        self.limiters = limiters
    
    async def acquire(self) -> None:
        """Acquire from all limiters."""
        for limiter in self.limiters:
            await limiter.acquire()
    
    async def __aenter__(self):
        """Context manager entry."""
        await self.acquire()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        pass
