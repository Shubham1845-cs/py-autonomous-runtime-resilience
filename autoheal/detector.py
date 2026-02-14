"""
Detection Engine Module

Analyzes telemetry data from the Monitor to detect service health issues
and recommend appropriate resilience patterns.

Key Innovation: Autonomous pattern selection based on failure signatures.
"""

import time
from typing import Dict, Optional, List
from enum import Enum


class HealthState(Enum):
    """Service health states"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    SLOW = "slow"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


class ResiliencePattern(Enum):
    """Available resilience patterns"""
    CIRCUIT_BREAKER = "circuit_breaker"
    RETRY = "retry"
    TIMEOUT = "timeout"
    NONE = None


class HealthDetector:
    """
    Analyzes service health and recommends resilience patterns.
    
    Uses threshold-based detection with configurable sensitivity.
    """
    
    def __init__(self, monitor, 
                 critical_failure_threshold: float = 50.0,
                 degraded_failure_threshold: float = 20.0,
                 slow_latency_threshold: float = 3.0,
                 min_calls_required: int = 5):
        """
        Initialize the health detector.
        
        Args:
            monitor: TelemetryMonitor instance
            critical_failure_threshold: Failure rate % for CRITICAL state (default 50%)
            degraded_failure_threshold: Failure rate % for DEGRADED state (default 20%)
            slow_latency_threshold: Latency in seconds for SLOW state (default 3s)
            min_calls_required: Minimum calls needed for analysis (default 5)
        """
        self.monitor = monitor
        self.critical_threshold = critical_failure_threshold
        self.degraded_threshold = degraded_failure_threshold
        self.slow_threshold = slow_latency_threshold
        self.min_calls = min_calls_required
    
    def analyze_health(self, service_name: str, window_seconds: int = 60) -> Dict:
        """
        Analyze service health based on recent metrics.
        
        Args:
            service_name: Name of the service to analyze
            window_seconds: Time window for analysis (default 60s)
            
        Returns:
            Dictionary with health analysis results
        """
        metrics = self.monitor.get_metrics(service_name, window_seconds)
        
        if not metrics or len(metrics) < self.min_calls:
            return {
                "service": service_name,
                "state": HealthState.UNKNOWN.value,
                "failure_rate": 0.0,
                "avg_latency": 0.0,
                "total_calls": len(metrics) if metrics else 0,
                "recommendation": None,
                "timestamp": time.time()
            }
        
        failure_rate = self.monitor.calculate_failure_rate(service_name, window_seconds)
        avg_latency = self.monitor.calculate_avg_latency(service_name, window_seconds)
        
        # Determine health state based on thresholds
        state = self._determine_state(failure_rate, avg_latency)
        
        return {
            "service": service_name,
            "state": state.value,
            "failure_rate": round(failure_rate, 2),
            "avg_latency": round(avg_latency, 3),
            "total_calls": len(metrics),
            "timestamp": time.time(),
            "window_seconds": window_seconds
        }
    
    def _determine_state(self, failure_rate: float, avg_latency: float) -> HealthState:
        """Determine health state from metrics."""
        if failure_rate >= self.critical_threshold:
            return HealthState.CRITICAL
        elif failure_rate >= self.degraded_threshold:
            return HealthState.DEGRADED
        elif avg_latency > self.slow_threshold:
            return HealthState.SLOW
        else:
            return HealthState.HEALTHY
    
    def recommend_pattern(self, service_name: str, window_seconds: int = 60) -> Optional[Dict]:
        """
        Recommend a resilience pattern based on failure analysis.
        
        Args:
            service_name: Service to analyze
            window_seconds: Analysis window
            
        Returns:
            Recommendation dictionary or None if no pattern needed
        """
        health = self.analyze_health(service_name, window_seconds)
        state = HealthState(health["state"])
        
        if state == HealthState.HEALTHY or state == HealthState.UNKNOWN:
            return None
        
        failure_rate = health["failure_rate"]
        avg_latency = health["avg_latency"]
        
        # Analyze error patterns
        metrics = self.monitor.get_metrics(service_name, window_seconds)
        error_analysis = self._analyze_errors(metrics)
        
        # Decision tree for pattern selection
        pattern, reason, config = self._select_pattern(
            state, failure_rate, avg_latency, error_analysis
        )
        
        if pattern == ResiliencePattern.NONE:
            return None
        
        return {
            "pattern": pattern.value,
            "reason": reason,
            "config": config,
            "health_state": state.value,
            "timestamp": time.time()
        }
    
    def _analyze_errors(self, metrics: List[Dict]) -> Dict:
        """Analyze error patterns in metrics."""
        if not metrics:
            return {
                "error_503_rate": 0.0,
                "error_500_rate": 0.0,
                "error_timeout_rate": 0.0,
                "error_connection_rate": 0.0
            }
        
        total = len(metrics)
        error_503 = sum(1 for m in metrics if m["status"] == 503)
        error_500 = sum(1 for m in metrics if m["status"] == 500)
        error_timeout = sum(1 for m in metrics 
                           if m["error"] and "timeout" in m["error"].lower())
        error_connection = sum(1 for m in metrics if m["status"] == 0)
        
        return {
            "error_503_rate": (error_503 / total) * 100,
            "error_500_rate": (error_500 / total) * 100,
            "error_timeout_rate": (error_timeout / total) * 100,
            "error_connection_rate": (error_connection / total) * 100,
            "total_errors": sum(1 for m in metrics if m["status"] >= 400 or m["status"] == 0)
        }
    
    def _select_pattern(self, state: HealthState, failure_rate: float, 
                       avg_latency: float, error_analysis: Dict) -> tuple:
        """
        Select appropriate resilience pattern based on failure signature.
        
        Returns:
            (pattern, reason, config)
        """
        # High failure rate → Circuit Breaker
        if failure_rate >= self.critical_threshold:
            return (
                ResiliencePattern.CIRCUIT_BREAKER,
                f"High failure rate ({failure_rate}% >= {self.critical_threshold}%)",
                {
                    "failure_threshold": 5,
                    "timeout_seconds": 30,
                    "half_open_max_calls": 1
                }
            )
        
        # Many 503 errors (service overload) → Retry
        if error_analysis["error_503_rate"] > 30:
            return (
                ResiliencePattern.RETRY,
                f"High rate of 503 errors ({error_analysis['error_503_rate']:.1f}%), indicating service overload",
                {
                    "max_attempts": 3,
                    "backoff_base": 2,
                    "max_delay": 10,
                    "jitter": True
                }
            )
        
        # High latency → Timeout
        if avg_latency > self.slow_threshold:
            return (
                ResiliencePattern.TIMEOUT,
                f"High average latency ({avg_latency:.2f}s > {self.slow_threshold}s)",
                {
                    "max_seconds": min(avg_latency * 0.5, 5.0)  # 50% of current latency, max 5s
                }
            )
        
        # Moderate failures with timeouts → Retry
        if error_analysis["error_timeout_rate"] > 20:
            return (
                ResiliencePattern.RETRY,
                f"High timeout rate ({error_analysis['error_timeout_rate']:.1f}%)",
                {
                    "max_attempts": 3,
                    "backoff_base": 2,
                    "max_delay": 10,
                    "jitter": True
                }
            )
        
        # Connection failures → Circuit Breaker
        if error_analysis["error_connection_rate"] > 30:
            return (
                ResiliencePattern.CIRCUIT_BREAKER,
                f"High connection failure rate ({error_analysis['error_connection_rate']:.1f}%)",
                {
                    "failure_threshold": 3,
                    "timeout_seconds": 60,
                    "half_open_max_calls": 1
                }
            )
        
        # Default: no pattern
        return (ResiliencePattern.NONE, "", {})
    
    def should_inject_pattern(self, service_name: str, 
                              persistence_seconds: int = 30) -> tuple:
        """
        Determine if a pattern should be injected now.
        
        Args:
            service_name: Service to check
            persistence_seconds: How long issue must persist (default 30s)
            
        Returns:
            (should_inject: bool, recommendation: Dict or None)
        """
        recommendation = self.recommend_pattern(service_name)
        
        if not recommendation:
            return False, None
        
        health = self.analyze_health(service_name)
        state = HealthState(health["state"])
        
        # Always inject for CRITICAL state
        if state == HealthState.CRITICAL:
            return True, recommendation
        
        # For DEGRADED or SLOW, check if it persists
        if state in [HealthState.DEGRADED, HealthState.SLOW]:
            # Check if degraded for at least persistence_seconds
            old_metrics = self.monitor.get_metrics(service_name, persistence_seconds)
            if len(old_metrics) >= self.min_calls:
                return True, recommendation
        
        return False, None
    
    def should_remove_pattern(self, service_name: str, 
                             grace_period_seconds: int = 300) -> bool:
        """
        Determine if an injected pattern should be removed.
        
        Args:
            service_name: Service to check
            grace_period_seconds: How long service must be healthy (default 300s = 5min)
            
        Returns:
            True if pattern should be removed
        """
        # Check health over grace period
        health = self.analyze_health(service_name, grace_period_seconds)
        state = HealthState(health["state"])
        
        # Remove if healthy for the entire grace period
        if state == HealthState.HEALTHY:
            metrics = self.monitor.get_metrics(service_name, grace_period_seconds)
            if len(metrics) >= grace_period_seconds / 5:  # At least 1 call per 5 seconds
                return True
        
        return False


# Convenience function to create a detector
def create_detector(monitor, **kwargs):
    """Create a HealthDetector instance."""
    return HealthDetector(monitor, **kwargs)
