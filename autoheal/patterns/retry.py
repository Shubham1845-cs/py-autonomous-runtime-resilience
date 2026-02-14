"""
Retry Pattern with Exponential Backoff

Automatically retries failed requests with increasing delay between attempts.

Features:
- Exponential backoff (2^attempt)
- Configurable maximum delay
- Jitter to prevent thundering herd
- Smart retry decision (don't retry client errors)
"""

import time
import random
from typing import Callable, Any, Optional


class RetryExhaustedError(Exception):
    """Raised when all retry attempts are exhausted"""
    pass


class RetryPolicy:
    """
    Retry policy with exponential backoff and jitter.
    """
    
    def __init__(self, max_attempts: int = 3,
                 backoff_base: float = 2.0,
                 max_delay: float = 10.0,
                 jitter: bool = True):
        """
        Initialize retry policy.
        
        Args:
            max_attempts: Maximum retry attempts (default 3)
            backoff_base: Base for exponential backoff (default 2)
            max_delay: Maximum delay between retries in seconds (default 10)
            jitter: Add randomness to prevent thundering herd (default True)
        """
        self.max_attempts = max_attempts
        self.backoff_base = backoff_base
        self.max_delay = max_delay
        self.jitter = jitter
    
    def execute(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute a function with retry logic.
        
        Args:
            func: Function to execute
            *args, **kwargs: Arguments to pass to function
            
        Returns:
            Result from function
            
        Raises:
            RetryExhaustedError: If all attempts fail
            Exception: Last exception if retries exhausted
        """
        last_exception = None
        
        for attempt in range(1, self.max_attempts + 1):
            try:
                result = func(*args, **kwargs)
                if attempt > 1:
                    print(f"[Retry] Success on attempt {attempt}/{self.max_attempts}")
                return result
                
            except Exception as e:
                last_exception = e
                
                # Check if we should retry this exception
                if not self._should_retry(e, attempt):
                    print(f"[Retry] Non-retryable error: {type(e).__name__}")
                    raise
                
                # Last attempt?
                if attempt >= self.max_attempts:
                    print(f"[Retry] All {self.max_attempts} attempts exhausted")
                    raise RetryExhaustedError(
                        f"Failed after {self.max_attempts} attempts"
                    ) from last_exception
                
                # Calculate delay and wait
                delay = self._calculate_delay(attempt)
                print(f"[Retry] Attempt {attempt}/{self.max_attempts} failed, "
                      f"retrying in {delay:.2f}s... ({type(e).__name__})")
                time.sleep(delay)
        
        # Should never reach here, but just in case
        raise last_exception
    
    def _should_retry(self, exception: Exception, attempt: int) -> bool:
        """
        Decide if we should retry based on exception type.
        
        Args:
            exception: The exception that was raised
            attempt: Current attempt number
            
        Returns:
            True if should retry, False otherwise
        """
        # Don't retry on client errors (4xx)
        if hasattr(exception, 'response'):
            status_code = getattr(exception.response, 'status_code', None)
            if status_code and 400 <= status_code < 500:
                # Client error, don't retry
                return False
        
        # Retry on server errors (5xx) and network issues
        return True
    
    def _calculate_delay(self, attempt: int) -> float:
        """
        Calculate delay for next retry using exponential backoff.
        
        Args:
            attempt: Current attempt number (1-indexed)
            
        Returns:
            Delay in seconds
        """
        # Exponential: base^(attempt-1)
        # Attempt 1: 2^0 = 1s
        # Attempt 2: 2^1 = 2s
        # Attempt 3: 2^2 = 4s
        delay = self.backoff_base ** (attempt - 1)
        
        # Cap at max_delay
        delay = min(delay, self.max_delay)
        
        # Add jitter (randomness) to prevent thundering herd
        if self.jitter:
            jitter_amount = random.uniform(0, delay * 0.1)  # ±10% jitter
            delay += jitter_amount
        
        return delay
