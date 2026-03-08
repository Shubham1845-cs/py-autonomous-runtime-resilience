import pytest
import time
from autoheal.patterns.circuit_breaker import CircuitBreaker, CircuitState, CircuitBreakerOpenError
from autoheal.patterns.retry import RetryPolicy, RetryExhaustedError
from autoheal.patterns.timeout import TimeoutGuard, TimeoutError

# --- Circuit Breaker Tests ---
def test_circuit_breaker_transitions():
    cb = CircuitBreaker(failure_threshold=2, recovery_timeout=0.5)
    
    # 2 failures -> OPEN
    with pytest.raises(ValueError):
        cb.execute(lambda: exec('raise ValueError("fail")'))
    with pytest.raises(ValueError):
        cb.execute(lambda: exec('raise ValueError("fail")'))
    
    assert cb.state == CircuitState.OPEN
    
    # Should fail fast now
    with pytest.raises(CircuitBreakerOpenError):
        cb.execute(lambda: "never runs")
        
    # Wait for recovery
    time.sleep(0.6)
    assert cb.state == CircuitState.HALF_OPEN
    
    # Success -> CLOSED
    assert cb.execute(lambda: "yay") == "yay"
    assert cb.state == CircuitState.CLOSED

# --- Retry Tests ---
def test_retry_success_after_failure():
    attempts = 0
    def failing_func():
        nonlocal attempts
        attempts += 1
        if attempts < 2: raise ValueError("transient")
        return "finally"
    
    retry = RetryPolicy(max_attempts=3, backoff_base=0.1)
    result = retry.execute(failing_func)
    assert result == "finally"
    assert attempts == 2

def test_retry_exhaustion():
    retry = RetryPolicy(max_attempts=2, backoff_base=0.1)
    with pytest.raises(RetryExhaustedError):
        retry.execute(lambda: exec('raise ValueError("always-fails")'))

# --- Timeout Tests ---
def test_timeout_success():
    guard = TimeoutGuard(max_seconds=1.0)
    result = guard.execute(lambda: "fast")
    assert result == "fast"

def test_timeout_failure():
    guard = TimeoutGuard(max_seconds=0.2)
    def slow_func():
        time.sleep(0.5)
        return "too slow"
    
    with pytest.raises(TimeoutError):
        guard.execute(slow_func)
