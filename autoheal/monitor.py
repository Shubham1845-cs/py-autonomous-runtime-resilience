"""
Telemetry Monitor Module

This module provides runtime monitoring of HTTP service calls without modifying
application code. It uses monkey patching to intercept requests library calls
and collect telemetry data (latency, status codes, timestamps).

Key Innovation: Zero-touch instrumentation via runtime interception.
"""

import time
import threading
from collections import deque, defaultdict
from urllib.parse import urlparse
import functools
from typing import Dict, List, Optional, Tuple


class TelemetryMonitor:
    """
    Monitors all outgoing HTTP calls and maintains a sliding window of metrics.
    
    Thread-safe implementation using locks for concurrent service calls.
    """
    
    def __init__(self, window_seconds: int = 60, max_entries_per_service: int = 1000):
        """
        Initialize the telemetry monitor.
        
        Args:
            window_seconds: How long to keep metrics (default 60 seconds)
            max_entries_per_service: Maximum entries to keep per service
        """
        self.window_seconds = window_seconds
        self.max_entries = max_entries_per_service
        
        # Store metrics per service: {"service_name": deque([{...}, {...}])}
        self.metrics: Dict[str, deque] = defaultdict(
            lambda: deque(maxlen=self.max_entries)
        )
        
        # Thread lock for concurrent access
        self._lock = threading.Lock()
        
        # Track if monitor is installed
        self._installed = False
        
        # Store original functions for restoration
        self._original_functions = {}
    
    def track_call(self, service_name: str, duration: float, status_code: int, 
                   error: Optional[str] = None):
        """
        Record a single service call's telemetry.
        
        Args:
            service_name: Name of the target service (extracted from URL)
            duration: Call duration in seconds
            status_code: HTTP status code (200, 500, etc.)
            error: Error message if call failed
        """
        with self._lock:
            self.metrics[service_name].append({
                "timestamp": time.time(),
                "duration": duration,
                "status": status_code,
                "error": error
            })
    
    def get_metrics(self, service_name: str, window_seconds: Optional[int] = None) -> List[Dict]:
        """
        Retrieve recent metrics for a service within the time window.
        
        Args:
            service_name: Name of the service
            window_seconds: Time window in seconds (default: use constructor value)
            
        Returns:
            List of metric dictionaries sorted by timestamp
        """
        window = window_seconds or self.window_seconds
        cutoff_time = time.time() - window
        
        with self._lock:
            if service_name not in self.metrics:
                return []
            
            # Filter metrics within the time window
            return [
                m for m in self.metrics[service_name]
                if m["timestamp"] >= cutoff_time
            ]
    
    def calculate_failure_rate(self, service_name: str, window_seconds: Optional[int] = None) -> float:
        """
        Calculate failure rate (percentage) for a service.
        
        Args:
            service_name: Name of the service
            window_seconds: Time window to analyze
            
        Returns:
            Failure rate as percentage (0-100). Returns 0 if no data.
        """
        metrics = self.get_metrics(service_name, window_seconds)
        
        if not metrics:
            return 0.0
        
        total_calls = len(metrics)
        failed_calls = sum(1 for m in metrics if m["status"] >= 400)
        
        return (failed_calls / total_calls) * 100 if total_calls > 0 else 0.0
    
    def calculate_avg_latency(self, service_name: str, window_seconds: Optional[int] = None) -> float:
        """
        Calculate average latency for a service.
        
        Args:
            service_name: Name of the service
            window_seconds: Time window to analyze
            
        Returns:
            Average latency in seconds. Returns 0 if no data.
        """
        metrics = self.get_metrics(service_name, window_seconds)
        
        if not metrics:
            return 0.0
        
        total_duration = sum(m["duration"] for m in metrics)
        return total_duration / len(metrics)
    
    def get_all_services(self) -> List[str]:
        """
        Get list of all monitored services.
        
        Returns:
            List of service names
        """
        with self._lock:
            return list(self.metrics.keys())
    
    def clear_metrics(self, service_name: Optional[str] = None):
        """
        Clear metrics for a specific service or all services.
        
        Args:
            service_name: Service to clear. If None, clears all.
        """
        with self._lock:
            if service_name:
                if service_name in self.metrics:
                    self.metrics[service_name].clear()
            else:
                self.metrics.clear()
    
    def get_health_summary(self, service_name: str) -> Dict:
        """
        Get comprehensive health summary for a service.
        
        Args:
            service_name: Name of the service
            
        Returns:
            Dictionary with health metrics
        """
        metrics = self.get_metrics(service_name)
        
        if not metrics:
            return {
                "service": service_name,
                "status": "unknown",
                "total_calls": 0,
                "failure_rate": 0.0,
                "avg_latency": 0.0
            }
        
        failure_rate = self.calculate_failure_rate(service_name)
        avg_latency = self.calculate_avg_latency(service_name)
        
        # Determine health status
        if failure_rate >= 50:
            status = "critical"
        elif failure_rate >= 20:
            status = "degraded"
        else:
            status = "healthy"
        
        return {
            "service": service_name,
            "status": status,
            "total_calls": len(metrics),
            "failure_rate": round(failure_rate, 2),
            "avg_latency": round(avg_latency, 3),
            "window_seconds": self.window_seconds
        }


# Global monitor instance
_monitor = TelemetryMonitor()


def install_monitor():
    """
    Install the monitor by monkey-patching the requests library.
    
    This function intercepts all HTTP calls made via the requests library
    and automatically collects telemetry without modifying application code.
    
    Innovation: Runtime instrumentation without code changes.
    """
    if _monitor._installed:
        print("[AutoHeal] Monitor already installed")
        return
    
    try:
        import requests
    except ImportError:
        raise ImportError("requests library is required. Install with: pip install requests")
    
    # Save original functions
    _monitor._original_functions['get'] = requests.get
    _monitor._original_functions['post'] = requests.post
    _monitor._original_functions['put'] = requests.put
    _monitor._original_functions['delete'] = requests.delete
    _monitor._original_functions['patch'] = requests.patch
    
    def _extract_service_name(url: str) -> str:
        """Extract service name from URL."""
        parsed = urlparse(url)
        # Use hostname as service name
        return parsed.netloc or "unknown"
    
    def _create_monitored_wrapper(original_func):
        """Create a wrapper that monitors the original function."""
        @functools.wraps(original_func)
        def wrapper(url, *args, **kwargs):
            service_name = _extract_service_name(url)
            start_time = time.time()
            error = None
            status_code = 0
            
            try:
                response = original_func(url, *args, **kwargs)
                status_code = response.status_code
                return response
            except Exception as e:
                error = str(e)
                status_code = 0  # Connection failed
                raise
            finally:
                duration = time.time() - start_time
                _monitor.track_call(service_name, duration, status_code, error)
        
        return wrapper
    
    # Replace requests functions with monitored versions
    requests.get = _create_monitored_wrapper(_monitor._original_functions['get'])
    requests.post = _create_monitored_wrapper(_monitor._original_functions['post'])
    requests.put = _create_monitored_wrapper(_monitor._original_functions['put'])
    requests.delete = _create_monitored_wrapper(_monitor._original_functions['delete'])
    requests.patch = _create_monitored_wrapper(_monitor._original_functions['patch'])
    
    _monitor._installed = True
    print("[AutoHeal] ✅ Monitor installed successfully - now tracking all HTTP calls")


def uninstall_monitor():
    """
    Restore original requests library functions.
    """
    if not _monitor._installed:
        print("[AutoHeal] Monitor not installed")
        return
    
    try:
        import requests
        requests.get = _monitor._original_functions['get']
        requests.post = _monitor._original_functions['post']
        requests.put = _monitor._original_functions['put']
        requests.delete = _monitor._original_functions['delete']
        requests.patch = _monitor._original_functions['patch']
        
        _monitor._installed = False
        print("[AutoHeal] ✅ Monitor uninstalled")
    except Exception as e:
        print(f"[AutoHeal] ⚠️ Error uninstalling monitor: {e}")


# Convenience functions using the global monitor
def get_metrics(service_name: str, window_seconds: Optional[int] = None) -> List[Dict]:
    """Get metrics for a service."""
    return _monitor.get_metrics(service_name, window_seconds)


def calculate_failure_rate(service_name: str, window_seconds: Optional[int] = None) -> float:
    """Calculate failure rate for a service."""
    return _monitor.calculate_failure_rate(service_name, window_seconds)


def calculate_avg_latency(service_name: str, window_seconds: Optional[int] = None) -> float:
    """Calculate average latency for a service."""
    return _monitor.calculate_avg_latency(service_name, window_seconds)


def get_health_summary(service_name: str) -> Dict:
    """Get health summary for a service."""
    return _monitor.get_health_summary(service_name)


def get_all_services() -> List[str]:
    """Get all monitored services."""
    return _monitor.get_all_services()


def clear_metrics(service_name: Optional[str] = None):
    """Clear metrics."""
    _monitor.clear_metrics(service_name)
