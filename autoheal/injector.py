"""
Pattern Injector Module

Dynamically wraps functions with resilience patterns at runtime.
This is the "hands" of AutoHeal-Py — once the detector recommends a pattern,
the injector applies it transparently to the target function.

Key Innovation:
  - Zero-modification injection: wraps any callable without touching its source
  - Per-service pattern management: inject/remove/swap patterns independently
  - Full injection audit trail: every injection/removal is timestamped and logged
  - Thread-safe: concurrent injections across services are safe
"""

import time
import threading
import functools
import logging
from typing import Dict, Optional, Callable, Any, List

from autoheal.patterns.circuit_breaker import CircuitBreaker, CircuitBreakerOpenError
from autoheal.patterns.retry import RetryPolicy
from autoheal.patterns.timeout import TimeoutGuard

logger = logging.getLogger("autoheal.injector")


# ─────────────────────────────────────────────
#  Data structures
# ─────────────────────────────────────────────

class InjectionRecord:
    """
    Represents a single pattern injection event.
    Stores the wrapped function, the original function, and metadata.
    """
    def __init__(self, service_name: str, pattern_type: str,
                 original_func: Callable, wrapped_func: Callable,
                 pattern_instance: Any, config: Dict):
        self.service_name    = service_name
        self.pattern_type    = pattern_type
        self.original_func   = original_func
        self.wrapped_func    = wrapped_func
        self.pattern_instance = pattern_instance
        self.config          = config
        self.injected_at     = time.time()
        self.removed_at: Optional[float] = None

    @property
    def is_active(self) -> bool:
        return self.removed_at is None

    @property
    def age_seconds(self) -> float:
        return time.time() - self.injected_at

    def to_dict(self) -> Dict:
        return {
            "service":      self.service_name,
            "pattern":      self.pattern_type,
            "config":       self.config,
            "injected_at":  self.injected_at,
            "removed_at":   self.removed_at,
            "active":       self.is_active,
            "age_seconds":  round(self.age_seconds, 1),
        }


# ─────────────────────────────────────────────
#  Main Injector
# ─────────────────────────────────────────────

class PatternInjector:
    """
    Dynamically injects resilience patterns into callables at runtime.

    Usage:
        injector = PatternInjector()

        # Wrap a function with circuit breaker
        protected_fn = injector.inject(
            service_name = "payment-api",
            func         = original_get_payment,
            pattern_type = "circuit_breaker",
            config       = {"failure_threshold": 5, "timeout_seconds": 30}
        )

        # Call the protected function normally
        result = protected_fn(order_id)

        # Remove protection when service recovers
        injector.remove(service_name="payment-api")
    """

    def __init__(self):
        # Active injections: {service_name → InjectionRecord}
        self._active: Dict[str, InjectionRecord] = {}
        # Full history of all injections (including removed)
        self._history: List[InjectionRecord] = []
        self._lock = threading.Lock()

    # ──────────────────────────────────────────
    #  Public API
    # ──────────────────────────────────────────

    def inject(self, service_name: str, func: Callable,
               pattern_type: str, config: Dict) -> Callable:
        """
        Wrap a callable with a resilience pattern.

        Args:
            service_name: Logical name of the service (used for lookup/removal)
            func:         The original callable to protect
            pattern_type: One of "circuit_breaker", "retry", "timeout"
            config:       Pattern-specific configuration dict

        Returns:
            A transparently wrapped callable that applies the pattern
        """
        with self._lock:
            # If a pattern is already active for this service, remove it first
            if service_name in self._active:
                logger.info(
                    "[Injector] Replacing existing '%s' on '%s' with '%s'",
                    self._active[service_name].pattern_type, service_name, pattern_type
                )
                self._deactivate(service_name)

            # Build pattern instance + wrapper
            pattern_instance, wrapped = self._build_wrapper(func, pattern_type, config)

            record = InjectionRecord(
                service_name     = service_name,
                pattern_type     = pattern_type,
                original_func    = func,
                wrapped_func     = wrapped,
                pattern_instance = pattern_instance,
                config           = config,
            )

            self._active[service_name] = record
            self._history.append(record)

            logger.info(
                "[Injector] ✅ Injected '%s' on service '%s' (config=%s)",
                pattern_type, service_name, config
            )
            return wrapped

    def remove(self, service_name: str) -> bool:
        """
        Remove an active pattern injection for a service.

        Args:
            service_name: Service to un-protect

        Returns:
            True if a pattern was removed, False if none was active
        """
        with self._lock:
            if service_name not in self._active:
                logger.debug("[Injector] No active pattern for '%s' to remove.", service_name)
                return False
            self._deactivate(service_name)
            logger.info("[Injector] 🗑️  Removed pattern from service '%s'", service_name)
            return True

    def get_active(self, service_name: str) -> Optional[InjectionRecord]:
        """Return the active injection record for a service, or None."""
        with self._lock:
            return self._active.get(service_name)

    def get_all_active(self) -> List[InjectionRecord]:
        """Return all currently active injection records."""
        with self._lock:
            return list(self._active.values())

    def get_history(self) -> List[InjectionRecord]:
        """Return the full injection history (active + removed)."""
        with self._lock:
            return list(self._history)

    def active_count(self) -> int:
        with self._lock:
            return len(self._active)

    def has_pattern(self, service_name: str) -> bool:
        with self._lock:
            return service_name in self._active

    def get_pattern_type(self, service_name: str) -> Optional[str]:
        with self._lock:
            rec = self._active.get(service_name)
            return rec.pattern_type if rec else None

    def summary(self) -> Dict:
        """High-level summary for dashboard and API."""
        with self._lock:
            return {
                "active_injections": len(self._active),
                "total_injections":  len(self._history),
                "services": [r.to_dict() for r in self._active.values()],
            }

    # ──────────────────────────────────────────
    #  Internal helpers
    # ──────────────────────────────────────────

    def _deactivate(self, service_name: str):
        """Mark an injection as removed (must be called under self._lock)."""
        record = self._active.pop(service_name)
        record.removed_at = time.time()

    def _build_wrapper(self, func: Callable, pattern_type: str,
                       config: Dict) -> tuple:
        """
        Build (pattern_instance, wrapped_callable) for the given pattern type.
        """
        if pattern_type == "circuit_breaker":
            return self._wrap_circuit_breaker(func, config)
        elif pattern_type == "retry":
            return self._wrap_retry(func, config)
        elif pattern_type == "timeout":
            return self._wrap_timeout(func, config)
        else:
            raise ValueError(f"Unknown pattern type: '{pattern_type}'. "
                             f"Choose from: circuit_breaker, retry, timeout")

    def _wrap_circuit_breaker(self, func: Callable, config: Dict) -> tuple:
        cb = CircuitBreaker(
            failure_threshold   = config.get("failure_threshold",   5),
            timeout_seconds     = config.get("timeout_seconds",     30),
            half_open_max_calls = config.get("half_open_max_calls", 1),
        )

        @functools.wraps(func)
        def wrapped(*args, **kwargs):
            return cb.execute(func, *args, **kwargs)

        return cb, wrapped

    def _wrap_retry(self, func: Callable, config: Dict) -> tuple:
        retry = RetryPolicy(
            max_attempts = config.get("max_attempts", 3),
            backoff_base = config.get("backoff_base", 2.0),
            max_delay    = config.get("max_delay",    10.0),
            jitter       = config.get("jitter",       True),
        )

        @functools.wraps(func)
        def wrapped(*args, **kwargs):
            return retry.execute(func, *args, **kwargs)

        return retry, wrapped

    def _wrap_timeout(self, func: Callable, config: Dict) -> tuple:
        t = TimeoutGuard(
            max_seconds = config.get("max_seconds", 5.0),
        )

        @functools.wraps(func)
        def wrapped(*args, **kwargs):
            return t.execute(func, *args, **kwargs)

        return t, wrapped


# ─────────────────────────────────────────────
#  Decorator API  (optional, dev-friendly)
# ─────────────────────────────────────────────

def with_circuit_breaker(failure_threshold: int = 5,
                          timeout_seconds: int = 30,
                          half_open_max_calls: int = 1):
    """
    Decorator: protect a function with a Circuit Breaker.

    Example::

        @with_circuit_breaker(failure_threshold=3, timeout_seconds=60)
        def call_payment_api(order_id):
            return requests.get(f"/payment/{order_id}")
    """
    def decorator(func):
        cb = CircuitBreaker(failure_threshold, timeout_seconds, half_open_max_calls)

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            return cb.execute(func, *args, **kwargs)

        wrapper._circuit_breaker = cb   # expose for introspection
        return wrapper
    return decorator


def with_retry(max_attempts: int = 3, backoff_base: float = 2.0,
               max_delay: float = 10.0, jitter: bool = True):  # noqa
    """
    Decorator: protect a function with Retry + exponential backoff.

    Example::

        @with_retry(max_attempts=3, backoff_base=2, jitter=True)
        def call_inventory_api(item_id):
            return requests.get(f"/inventory/{item_id}")
    """
    def decorator(func):
        retry = RetryPolicy(max_attempts, backoff_base, max_delay, jitter)

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            return retry.execute(func, *args, **kwargs)

        wrapper._retry = retry
        return wrapper
    return decorator


def with_timeout(max_seconds: float = 5.0):
    """
    Decorator: protect a function with a Timeout guard.

    Example::

        @with_timeout(max_seconds=3.0)
        def call_slow_db(query):
            return db.execute(query)
    """
    def decorator(func):
        t = TimeoutGuard(max_seconds)

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            return t.execute(func, *args, **kwargs)

        wrapper._timeout = t
        return wrapper
    return decorator


# ─────────────────────────────────────────────
#  Module-level singleton (shared by agent)
# ─────────────────────────────────────────────
_injector: Optional[PatternInjector] = None


def get_injector() -> PatternInjector:
    """Return the global PatternInjector singleton, creating it if needed."""
    global _injector
    if _injector is None:
        _injector = PatternInjector()
    return _injector
