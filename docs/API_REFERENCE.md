# AutoHeal-Py API Reference

## `autoheal.monitor`

### `install_monitor()`
Patches the `requests` library globally. After this call, all `requests.get`, `post`, etc., are automatically tracked.

### `uninstall_monitor()`
Restores the original `requests` functions.

### `get_metrics(service_name: str, window_seconds: int = 60)`
Returns a list of raw call metrics for the specified service.

---

## `autoheal.agent`

### `create_agent(monitor, ...)`
Factory function to create an `AutoHealAgent`.
-   **Parameters**: `scan_interval`, `critical_threshold`, `degraded_threshold`, `slow_threshold`, `grace_period`.

### `agent.start()`
Starts the background daemon thread.

### `agent.stop()`
Gracefully stops the background thread.

### `agent.get_events(limit: int = 50)`
Returns the most recent event logs (injections, removals, health changes).

---

## `autoheal.injector`

### `get_injector()`
Returns the global `PatternInjector` singleton.

### `injector.inject(service, func, pattern_type, config)`
Manually injects a pattern into a callable.
-   **Patterns**: `"circuit_breaker"`, `"retry"`, `"timeout"`.

### `injector.remove(service)`
Removes active protection from a service.

---

## Decorators

### `@with_circuit_breaker(failure_threshold, timeout_seconds)`
Wraps a function with the Circuit Breaker pattern.

### `@with_retry(max_attempts, backoff_base, jitter)`
Wraps a function with the Exponential Backoff Retry pattern.

### `@with_timeout(max_seconds)`
Wraps a function with a Timeout guard.
