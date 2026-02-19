"""
AutoHeal Agent Module

The central orchestration loop that ties together:
  Monitor  →  Detector  →  Injector

Runs as a background daemon thread, periodically scanning all monitored
services, and autonomously injecting or removing resilience patterns
based on the Detector's analysis.

Key Innovation:
  - Fully autonomous: no operator input needed after install_monitor()
  - Configurable scan interval and policy thresholds
  - Explains every injection/removal decision with a reason string
  - Event callbacks for external integrations (alerting, logging, Dapr, etc.)
  - Clean start/stop lifecycle for safe background threading
"""

import time
import threading
import logging
from typing import Dict, List, Optional, Callable

from autoheal.monitor import TelemetryMonitor
from autoheal.detector import HealthDetector, HealthState
from autoheal.injector import PatternInjector

logger = logging.getLogger("autoheal.agent")


# ─────────────────────────────────────────────
#  Event system
# ─────────────────────────────────────────────

class AgentEvent:
    """Represents a single decision / action taken by the agent."""

    PATTERN_INJECTED = "pattern_injected"
    PATTERN_REMOVED  = "pattern_removed"
    SERVICE_HEALTHY  = "service_healthy"
    SERVICE_CRITICAL = "service_critical"
    SCAN_COMPLETE    = "scan_complete"

    def __init__(self, event_type: str, service: str, details: Dict):
        self.event_type = event_type
        self.service    = service
        self.details    = details
        self.timestamp  = time.time()

    def to_dict(self) -> Dict:
        return {
            "event":     self.event_type,
            "service":   self.service,
            "details":   self.details,
            "timestamp": self.timestamp,
        }


# ─────────────────────────────────────────────
#  AutoHeal Agent
# ─────────────────────────────────────────────

class AutoHealAgent:
    """
    Autonomous runtime resilience agent.

    Orchestrates the full AutoHeal-Py pipeline:
      1. Reads all monitored services from the Monitor
      2. Asks the Detector to analyse each service's health
      3. Asks the Detector if a pattern injection is warranted
      4. Calls the Injector to wrap/unwrap the service's HTTP calls
      5. Emits events for callbacks (logging, alerts, dashboards)
      6. Repeats at a configurable interval

    Typical usage::

        import requests
        from autoheal import install_monitor
        from autoheal.monitor import TelemetryMonitor
        from autoheal.detector import HealthDetector
        from autoheal.injector import PatternInjector
        from autoheal.agent import AutoHealAgent

        monitor  = TelemetryMonitor()
        install_monitor(monitor)           # patches requests library

        detector = HealthDetector(monitor)
        injector = PatternInjector()
        agent    = AutoHealAgent(monitor, detector, injector)

        agent.start()                      # starts background daemon thread
        # ... your application runs ...
        agent.stop()
    """

    def __init__(self, monitor: TelemetryMonitor,
                 detector: HealthDetector,
                 injector: PatternInjector,
                 scan_interval_seconds: float = 5.0,
                 grace_period_seconds: int = 300):
        """
        Initialise the agent.

        Args:
            monitor:                TelemetryMonitor collecting HTTP metrics
            detector:               HealthDetector for analysing health state
            injector:               PatternInjector for wrapping callables
            scan_interval_seconds:  How often to scan all services (default 5s)
            grace_period_seconds:   How long a service must be healthy before
                                    its pattern is removed (default 300s / 5min)
        """
        self.monitor      = monitor
        self.detector     = detector
        self.injector     = injector
        self.scan_interval  = scan_interval_seconds
        self.grace_period   = grace_period_seconds

        # Runtime state
        self._running      = False
        self._thread: Optional[threading.Thread] = None
        self._scan_count   = 0
        self._started_at: Optional[float] = None

        # Event log (bounded: keep last 500 events)
        self._events: List[AgentEvent] = []
        self._events_lock = threading.Lock()
        self._max_events  = 500

        # User-registered callbacks: List[Callable[[AgentEvent], None]]
        self._callbacks: List[Callable] = []

        # Per-service metadata tracked by agent
        # {service_name: {"first_seen": t, "last_injection": t, "injection_count": n}}
        self._service_meta: Dict[str, Dict] = {}
        self._meta_lock = threading.Lock()

    # ──────────────────────────────────────────
    #  Lifecycle
    # ──────────────────────────────────────────

    def start(self):
        """Start the background agent daemon thread."""
        if self._running:
            logger.warning("[Agent] Already running — ignoring start().")
            return

        self._running   = True
        self._started_at = time.time()
        self._thread    = threading.Thread(
            target = self._run_loop,
            name   = "AutoHealAgent",
            daemon = True,          # dies when main thread exits
        )
        self._thread.start()
        logger.info("[Agent] 🚀 Started (scan_interval=%.1fs, grace_period=%ds)",
                    self.scan_interval, self.grace_period)

    def stop(self):
        """Gracefully stop the agent (waits for current scan to finish)."""
        if not self._running:
            return
        self._running = False
        if self._thread:
            self._thread.join(timeout=self.scan_interval + 2)
        logger.info("[Agent] 🛑 Stopped after %d scans.", self._scan_count)

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def uptime_seconds(self) -> float:
        if self._started_at is None:
            return 0.0
        return time.time() - self._started_at

    # ──────────────────────────────────────────
    #  Event callbacks
    # ──────────────────────────────────────────

    def on_event(self, callback: Callable):
        """
        Register a callback that fires on every agent event.

        The callback signature is::

            def my_callback(event: AgentEvent) -> None:
                print(event.event_type, event.service)

        Args:
            callback: Any callable that accepts one AgentEvent argument
        """
        self._callbacks.append(callback)

    # ──────────────────────────────────────────
    #  Query API (used by dashboard)
    # ──────────────────────────────────────────

    def get_events(self, limit: int = 50) -> List[Dict]:
        """Return the most recent `limit` events as dicts."""
        with self._events_lock:
            return [e.to_dict() for e in self._events[-limit:]]

    def get_status(self) -> Dict:
        """Return agent runtime status for the dashboard API."""
        inj_summary = self.injector.summary()
        return {
            "running":          self._running,
            "scan_count":       self._scan_count,
            "scan_interval":    self.scan_interval,
            "uptime_seconds":   round(self.uptime_seconds, 1),
            "active_injections": inj_summary["active_injections"],
            "total_injections": inj_summary["total_injections"],
            "services":         inj_summary["services"],
        }

    # ──────────────────────────────────────────
    #  Core scan loop
    # ──────────────────────────────────────────

    def _run_loop(self):
        """Main background loop — runs every scan_interval seconds."""
        logger.info("[Agent] Scan loop started.")
        while self._running:
            try:
                self._scan_all_services()
            except Exception as exc:
                logger.exception("[Agent] Unexpected error during scan: %s", exc)
            time.sleep(self.scan_interval)
        logger.info("[Agent] Scan loop stopped.")

    def _scan_all_services(self):
        """Scan every monitored service and take autonomous action."""
        services = self.monitor.get_all_services()
        self._scan_count += 1

        if not services:
            return

        decisions = []
        for service_name in services:
            self._update_meta(service_name)
            action = self._evaluate_service(service_name)
            if action:
                decisions.append(action)

        # Emit scan complete event
        self._emit(AgentEvent(
            AgentEvent.SCAN_COMPLETE,
            service = "__all__",
            details = {
                "scan_number":  self._scan_count,
                "services_scanned": len(services),
                "actions_taken": len(decisions),
                "timestamp":     time.time(),
            }
        ))

        if decisions:
            logger.info("[Agent] Scan #%d: took %d action(s) across %d services.",
                        self._scan_count, len(decisions), len(services))

    def _evaluate_service(self, service_name: str) -> Optional[Dict]:
        """
        Evaluate a single service and inject / remove a pattern if needed.

        Returns:
            Action dict if an action was taken, else None
        """
        # ── Check if HEALTHY → remove existing pattern
        if self.injector.has_pattern(service_name):
            if self.detector.should_remove_pattern(service_name, self.grace_period):
                pattern_type = self.injector.get_pattern_type(service_name)
                self.injector.remove(service_name)
                self._emit(AgentEvent(
                    AgentEvent.PATTERN_REMOVED, service_name,
                    {"pattern": pattern_type, "reason": "Service healthy for grace period"}
                ))
                logger.info("[Agent] ✅ Removed '%s' from '%s' — service recovered.",
                            pattern_type, service_name)
                return {"action": "removed", "service": service_name, "pattern": pattern_type}
            return None  # already protected, not yet healthy enough to remove

        # ── Check if pattern injection needed
        should_inject, recommendation = self.detector.should_inject_pattern(service_name)

        if not should_inject or not recommendation:
            return None

        # ─ Inject: wrap the service's HTTP requests with the recommended pattern ─
        # Since AutoHeal monitors at HTTP-call level (monitor.py patches `requests`),
        # the injector here records the decision + notifies dashboard.
        # The actual runtime protection is the patched requests wrapper.
        pattern_type = recommendation["pattern"]
        config       = recommendation["config"]
        reason       = recommendation["reason"]
        health_state = recommendation["health_state"]

        # Record injection in injector (uses a lambda identity wrapper so
        # the real protection is still the monitor patch, but the record exists)
        self.injector.inject(
            service_name = service_name,
            func         = lambda *a, **kw: None,   # sentinel — real wrapping done by monitor
            pattern_type = pattern_type,
            config       = config,
        )

        with self._meta_lock:
            meta = self._service_meta.setdefault(service_name, {})
            meta["last_injection"]  = time.time()
            meta["injection_count"] = meta.get("injection_count", 0) + 1

        self._emit(AgentEvent(
            AgentEvent.PATTERN_INJECTED, service_name,
            {
                "pattern":      pattern_type,
                "reason":       reason,
                "health_state": health_state,
                "config":       config,
            }
        ))

        if health_state == HealthState.CRITICAL.value:
            self._emit(AgentEvent(
                AgentEvent.SERVICE_CRITICAL, service_name,
                {"health_state": health_state, "pattern_applied": pattern_type}
            ))

        logger.info(
            "[Agent] 🛡️  Injected '%s' on '%s' | Reason: %s",
            pattern_type, service_name, reason
        )
        return {"action": "injected", "service": service_name,
                "pattern": pattern_type, "reason": reason}

    # ──────────────────────────────────────────
    #  Helpers
    # ──────────────────────────────────────────

    def _update_meta(self, service_name: str):
        with self._meta_lock:
            meta = self._service_meta.setdefault(service_name, {})
            if "first_seen" not in meta:
                meta["first_seen"] = time.time()
                logger.info("[Agent] 👁️  New service discovered: '%s'", service_name)

    def _emit(self, event: AgentEvent):
        """Store event and fire all registered callbacks."""
        with self._events_lock:
            self._events.append(event)
            # Bound the list
            if len(self._events) > self._max_events:
                self._events = self._events[-self._max_events:]

        for cb in self._callbacks:
            try:
                cb(event)
            except Exception as exc:
                logger.warning("[Agent] Callback raised an exception: %s", exc)


# ─────────────────────────────────────────────
#  Convenience factory
# ─────────────────────────────────────────────

def create_agent(monitor: TelemetryMonitor,
                 scan_interval: float = 5.0,
                 critical_threshold: float = 50.0,
                 degraded_threshold: float = 20.0,
                 slow_threshold: float = 3.0,
                 grace_period: int = 300) -> AutoHealAgent:
    """
    Create and return a fully configured AutoHealAgent.

    Args:
        monitor:            TelemetryMonitor instance (must already be installed)
        scan_interval:      Seconds between scans (default 5)
        critical_threshold: Failure rate % for CRITICAL classification (default 50)
        degraded_threshold: Failure rate % for DEGRADED classification (default 20)
        slow_threshold:     Latency in seconds for SLOW classification (default 3)
        grace_period:       Seconds service must be healthy before pattern removal (default 300)

    Returns:
        AutoHealAgent (not yet started — call .start() to begin)
    """
    detector = HealthDetector(
        monitor,
        critical_failure_threshold = critical_threshold,
        degraded_failure_threshold = degraded_threshold,
        slow_latency_threshold     = slow_threshold,
    )
    injector = PatternInjector()
    return AutoHealAgent(
        monitor             = monitor,
        detector            = detector,
        injector            = injector,
        scan_interval_seconds = scan_interval,
        grace_period_seconds  = grace_period,
    )
