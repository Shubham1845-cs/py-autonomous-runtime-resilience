# AutoHeal-Py: Patterns Deep Dive

This document provides formal specifications and implementation details for the resilience patterns provided by AutoHeal-Py.

## 1. Circuit Breaker (`CircuitBreaker`)

### Philosophy
Prevent cascading failures by "tripping" the connection to a failing service.

### State Machine
- **CLOSED**: Normal operation. Failures are counted.
- **OPEN**: Failures exceed `failure_threshold`. All calls fail-fast with `CircuitBreakerOpenError`.
- **HALF_OPEN**: After `timeout_seconds` in OPEN state, a single "probe" call is allowed.
    -   Success → Return to CLOSED.
    -   Failure → Return to OPEN.

### Implementation Feature
Uses a `threading.Lock` to ensure state transitions are atomic in highly concurrent environments.

## 2. Exponential Backoff Retry (`RetryPolicy`)

### Philosophy
Mask transient network errors (UDP drops, temporary DNS issues, 503 Overloads) without overwhelming the target service.

### Optimization: Jitter
We implement **Full Jitter** to prevent the "Thundering Herd" problem.
-   `delay = random(0, base_delay * (2 ^ attempt))`
-   Max delay is capped at `max_delay`.

## 3. Timeout Guard (`TimeoutGuard`)

### Philosophy
Enforce strict execution bounds to prevent "slow loris" style resource exhaustion in the calling process.

### Implementation
-   Uses `threading.Timer` or `signal` depending on the operation type.
-   Raises a custom `TimeoutError` if the callable does not return within `max_seconds`.
-   **Critical for Sidecar Mode**: Prevents a single slow downstream service from locking up all worker threads in the main application.
