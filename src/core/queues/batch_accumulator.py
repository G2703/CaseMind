"""
Batch accumulator for efficient batching of items.
Accumulates items until batch size reached or timeout elapsed.
"""

import asyncio
import logging
from typing import List, Any, Callable, Optional
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class BatchItem:
    """Item in batch with metadata."""
    data: Any
    timestamp: datetime
    source_id: Optional[str] = None


class BatchAccumulator:
    """
    Accumulates items into batches for efficient processing.
    Flushes when batch size reached or timeout elapsed.
    """
    
    def __init__(
        self,
        batch_size: int,
        flush_timeout: float = 10.0,
        process_fn: Optional[Callable] = None
    ):
        """
        Initialize batch accumulator.
        
        Args:
            batch_size: Maximum items per batch
            flush_timeout: Seconds before flushing partial batch
            process_fn: Async function to process accumulated batch
        """
        self.batch_size = batch_size
        self.flush_timeout = flush_timeout
        self.process_fn = process_fn
        
        self.buffer: List[BatchItem] = []
        self.lock = asyncio.Lock()
        self._flush_task: Optional[asyncio.Task] = None
        self._running = False
        
        logger.info(f"BatchAccumulator created (size: {batch_size}, timeout: {flush_timeout}s)")
    
    async def add(self, item: Any, source_id: Optional[str] = None) -> None:
        """
        Add item to batch.
        
        Args:
            item: Item to add
            source_id: Optional source identifier for tracking
        """
        async with self.lock:
            batch_item = BatchItem(
                data=item,
                timestamp=datetime.now(),
                source_id=source_id
            )
            
            self.buffer.append(batch_item)
            logger.debug(f"Added item to batch (current size: {len(self.buffer)}/{self.batch_size})")
            
            # Flush if batch full
            if len(self.buffer) >= self.batch_size:
                logger.debug("Batch full, flushing immediately")
                await self._flush()
            elif not self._flush_task or self._flush_task.done():
                # Start timeout for partial batch
                self._flush_task = asyncio.create_task(self._flush_after_timeout())
    
    async def _flush_after_timeout(self) -> None:
        """Flush batch after timeout."""
        await asyncio.sleep(self.flush_timeout)
        
        async with self.lock:
            if self.buffer:
                logger.debug(f"Flush timeout reached, flushing {len(self.buffer)} items")
                await self._flush()
    
    async def _flush(self) -> None:
        """Flush current batch (must be called with lock held)."""
        if not self.buffer:
            return
        
        batch = self.buffer.copy()
        self.buffer.clear()
        
        # Cancel timeout task
        if self._flush_task and not self._flush_task.done():
            self._flush_task.cancel()
        
        logger.info(f"Flushing batch of {len(batch)} items")
        
        # Process batch if function provided
        if self.process_fn:
            try:
                await self.process_fn([item.data for item in batch])
                logger.debug(f"✓ Batch processed successfully")
            except Exception as e:
                logger.error(f"Batch processing failed: {e}")
    
    async def flush(self) -> None:
        """Manually flush current batch."""
        async with self.lock:
            await self._flush()
    
    def get_status(self) -> dict:
        """Get accumulator status."""
        return {
            "batch_size": self.batch_size,
            "flush_timeout": self.flush_timeout,
            "current_buffer_size": len(self.buffer),
            "buffer_fill_percent": (len(self.buffer) / self.batch_size) * 100
        }
