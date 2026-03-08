import pytest
import time
from autoheal.monitor import TelemetryMonitor

def test_track_call(monitor):
    monitor.track_call("test-service", duration=0.1, status_code=200)
    metrics = monitor.get_metrics("test-service")
    assert len(metrics) == 1
    assert metrics[0]["duration"] == 0.1
    assert metrics[0]["status"] == 200

def test_calculate_failure_rate(monitor):
    # 2 successes, 1 failure
    monitor.track_call("test-service", 0.1, 200)
    monitor.track_call("test-service", 0.1, 200)
    monitor.track_call("test-service", 0.1, 500)
    
    # 1/3 failure rate = 33.33%
    rate = monitor.calculate_failure_rate("test-service")
    assert 33.3 <= rate <= 33.4

def test_calculate_avg_latency(monitor):
    monitor.track_call("test-service", 0.1, 200)
    monitor.track_call("test-service", 0.3, 200)
    
    avg = monitor.calculate_avg_latency("test-service")
    assert avg == 0.2

def test_window_filtering(monitor):
    m = TelemetryMonitor(window_seconds=1)
    m.track_call("test-service", 0.1, 200)
    assert len(m.get_metrics("test-service")) == 1
    
    time.sleep(1.1)
    assert len(m.get_metrics("test-service")) == 0

def test_get_all_services(monitor):
    monitor.track_call("svc1", 0.1, 200)
    monitor.track_call("svc2", 0.1, 200)
    services = monitor.get_all_services()
    assert "svc1" in services
    assert "svc2" in services
    assert len(services) == 2
