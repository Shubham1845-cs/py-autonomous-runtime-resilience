"""
Circuit Breaker Pattern

Prevents cascading failures by failing fast when a service is unhealthy.

State Machine:
- CLOSED: Normal operation, calls pass through
- OPEN: Service is down, fail immediately
- HALF_OPEN: Testing recovery, allow limited calls
"""

import time
import threading
from enum import Enum
from typing import Callable, Any


class CircuitState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreakerOpenError(Exception):
    """Raised when circuit breaker is open"""
    pass


class CircuitBreaker:
    """
    Circuit breaker implementation with automatic state transitions.
    
    Thread-safe implementation using locks.
    """
    
    def __init__(self, failure_threshold: int = 5, 
                 timeout_seconds: int = 30,
                 half_open_max_calls: int = 1):
        """
        Initialize circuit breaker.
        
        Args:
            failure_threshold: Number of failures before opening (default 5)
            timeout_seconds: Time to wait before attempting recovery (default 30)
            half_open_max_calls: Max concurrent calls in HALF_OPEN state (default 1)
        """
        self.failure_threshold = failure_threshold
        self.timeout = timeout_seconds
        self.half_open_max = half_open_max_calls
        
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time = None
        self.half_open_calls = 0
        
        self._lock = threading.Lock()
    
    def execute(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute a function with circuit breaker protection.
        
        Args:
            func: Function to execute
            *args, **kwargs: Arguments to pass to function
            
        Returns:
            Result from function
            
        Raises:
            CircuitBreakerOpenError: If circuit is open
            Exception: Any exception from the wrapped function
        """
        with self._lock:
            # STATE: OPEN
            if self.state == CircuitState.OPEN:
                if self._should_attempt_reset():
                    print(f"[CircuitBreaker] Transitioning to HALF_OPEN (timeout expired)")
                    self.state = CircuitState.HALF_OPEN
                    self.half_open_calls = 0
                else:
                    raise CircuitBreakerOpenError(
                        f"Circuit breaker is OPEN. Failing fast. "
                        f"Retry after {self._get_remaining_timeout():.1f}s"
                    )
            
            # STATE: HALF_OPEN
            if self.state == CircuitState.HALF_OPEN:
                if self.half_open_calls >= self.half_open_max:
                    raise CircuitBreakerOpenError(
                        "Circuit breaker is HALF_OPEN, test call in progress"
                    )
                self.half_open_calls += 1
        
        # Execute the call (outside lock to allow concurrency)
        try:
            result = func(*args, **kwargs)
            self._record_success()
            return result
        except Exception as e:
            self._record_failure()
            raise
    
    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to try recovery."""
        if self.last_failure_time is None:
            return False
        elapsed = time.time() - self.last_failure_time
        return elapsed >= self.timeout
    
    def _get_remaining_timeout(self) -> float:
        """Get remaining timeout duration."""
        if self.last_failure_time is None:
            return 0.0
        elapsed = time.time() - self.last_failure_time
        return max(0.0, self.timeout - elapsed)
    
    def _record_success(self):
        """Handle successful call."""
        with self._lock:
            if self.state == CircuitState.HALF_OPEN:
                # Recovery successful
                print(f"[CircuitBreaker] Recovery successful → CLOSED")
                self.state = CircuitState.CLOSED
                self.failure_count = 0
                self.last_failure_time = None
            elif self.state == CircuitState.CLOSED:
                # Reset failure count on success
                self.failure_count = 0
    
    def _record_failure(self):
        """Handle failed call."""
        with self._lock:
            self.failure_count += 1
            self.last_failure_time = time.time()
            
            if self.state == CircuitState.HALF_OPEN:
                # Recovery failed, go back to OPEN
                print(f"[CircuitBreaker] Recovery failed → OPEN")
                self.state = CircuitState.OPEN
                self.half_open_calls = 0
            elif self.failure_count >= self.failure_threshold:
                # Too many failures, open circuit
                print(f"[CircuitBreaker] Failure threshold exceeded ({self.failure_count}) → OPEN")
                self.state = CircuitState.OPEN
    
    def get_state(self) -> CircuitState:
        """Get current circuit state."""
        with self._lock:
            return self.state
    
    def reset(self):
        """Manually reset circuit breaker to CLOSED state."""
        with self._lock:
            self.state = CircuitState.CLOSED
            self.failure_count = 0
            self.last_failure_time = None
            self.half_open_calls = 0
            print(f"[CircuitBreaker] Manually reset → CLOSED")
