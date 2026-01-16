"""
Rate limiter utility for web scraping.

Enforces minimum delay between requests to avoid being blocked.
"""

import asyncio
import time


class RateLimiter:
    """
    Simple rate limiter that enforces a minimum delay between requests.

    Args:
        min_delay_seconds: Minimum seconds to wait between requests (default: 30)
    """

    def __init__(self, min_delay_seconds: float = 30.0):
        self.min_delay_seconds = min_delay_seconds
        self._last_request_time: float = 0
        self._lock = asyncio.Lock()
        self._request_count = 0

    async def acquire(self) -> None:
        """
        Acquire permission to make a request.
        Will wait if necessary to respect the rate limit.
        """
        async with self._lock:
            now = time.time()
            elapsed = now - self._last_request_time

            if elapsed < self.min_delay_seconds and self._last_request_time > 0:
                wait_time = self.min_delay_seconds - elapsed
                await asyncio.sleep(wait_time)

            self._last_request_time = time.time()
            self._request_count += 1

    @property
    def request_count(self) -> int:
        """Total number of requests made."""
        return self._request_count

    def reset(self) -> None:
        """Reset the rate limiter state."""
        self._last_request_time = 0
        self._request_count = 0


class RateLimitExceeded(Exception):
    """Exception raised when rate limit would be exceeded."""
    pass
