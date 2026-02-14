"""
Resilience Patterns Package

Implementations of resilience patterns that can be dynamically injected:
- Circuit Breaker
- Retry with Exponential Backoff
- Timeout
"""

from .circuit_breaker import CircuitBreaker, CircuitState, CircuitBreakerOpenError
from .retry import RetryPolicy, RetryExhaustedError
from .timeout import TimeoutGuard, TimeoutError

__all__ = [
    "CircuitBreaker",
    "CircuitState",
    "CircuitBreakerOpenError",
    "RetryPolicy",
    "RetryExhaustedError",
    "TimeoutGuard",
    "TimeoutError"
]
