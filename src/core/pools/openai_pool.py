"""
OpenAI client pool with rate limiting.
Manages API client instances and enforces rate limits.
"""

import asyncio
import logging
from typing import Optional

from openai import OpenAI, AsyncOpenAI
from src.core.config import Config
from src.utils.rate_limiter import RateLimiter

logger = logging.getLogger(__name__)


class OpenAIClientPool:
    """
    OpenAI client pool with rate limiting.
    Provides rate-limited access to OpenAI API.
    """
    
    _instance: Optional['OpenAIClientPool'] = None
    
    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self, rpm: Optional[int] = None, config: Optional[Config] = None):
        """
        Initialize OpenAI client pool.
        
        Args:
            rpm: Requests per minute limit (defaults to config.openai_rpm)
            config: Configuration instance
        """
        # Only initialize once
        if hasattr(self, '_initialized') and self._initialized:
            return
        
        self.config = config or Config()
        self.rpm = rpm or int(os.getenv('OPENAI_RPM', '3'))
        self.client: Optional[AsyncOpenAI] = None
        self.rate_limiter: Optional[RateLimiter] = None
        self._initialized = False
        
        logger.info(f"OpenAIClientPool created with {self.rpm} RPM limit")
    
    async def initialize(self) -> None:
        """Initialize OpenAI client and rate limiter."""
        if self._initialized:
            logger.warning("OpenAIClientPool already initialized")
            return
        
        logger.info("Initializing OpenAI client...")
        
        try:
            # Create async OpenAI client
            self.client = AsyncOpenAI(api_key=self.config.openai_api_key)
            
            # Create rate limiter
            self.rate_limiter = RateLimiter(requests_per_minute=self.rpm)
            
            self._initialized = True
            logger.info(f"✓ OpenAI client initialized with {self.rpm} RPM limit")
            
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI client: {e}")
            raise
    
    async def create_chat_completion(self, **kwargs):
        """
        Create chat completion with rate limiting.
        
        Args:
            **kwargs: Arguments for OpenAI chat completion
            
        Returns:
            OpenAI chat completion response
        """
        if not self._initialized:
            raise RuntimeError("Client not initialized. Call initialize() first.")
        
        # Acquire rate limit token
        async with self.rate_limiter:
            logger.debug(f"Making OpenAI API call (model: {kwargs.get('model', 'unknown')})")
            
            try:
                response = await self.client.chat.completions.create(**kwargs)
                logger.debug("✓ OpenAI API call successful")
                return response
                
            except Exception as e:
                logger.error(f"OpenAI API call failed: {e}")
                raise
    
    async def close(self) -> None:
        """Cleanup resources."""
        logger.info("Closing OpenAIClientPool...")
        
        if self.client:
            await self.client.close()
        
        self.client = None
        self.rate_limiter = None
        self._initialized = False
        
        logger.info("✓ OpenAIClientPool closed")
    
    def get_status(self) -> dict:
        """Get pool status."""
        status = {
            "rpm": self.rpm,
            "initialized": self._initialized,
            "client_ready": self.client is not None
        }
        
        if self.rate_limiter:
            status["rate_limiter"] = self.rate_limiter.get_status()
        
        return status


import os
