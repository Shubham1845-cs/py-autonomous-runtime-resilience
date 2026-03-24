import pytest
from autoheal.detector import HealthState

def test_analyze_healthy(detector, monitor):
    # Need at least 5 calls by default
    for _ in range(10):
        monitor.track_call("svc", 0.1, 200)
    
    result = detector.analyze_health("svc")
    assert result["state"] == HealthState.HEALTHY.value

def test_analyze_degraded(detector, monitor):
    # 30% failure rate (threshold is 20)
    for _ in range(7): monitor.track_call("svc", 0.1, 200)
    for _ in range(3): monitor.track_call("svc", 0.1, 500)
    
    result = detector.analyze_health("svc")
    assert result["state"] == HealthState.DEGRADED.value

def test_analyze_critical(detector, monitor):
    # 60% failure rate (threshold is 50)
    for _ in range(4): monitor.track_call("svc", 0.1, 200)
    for _ in range(6): monitor.track_call("svc", 0.1, 503)
    
    result = detector.analyze_health("svc")
    assert result["state"] == HealthState.CRITICAL.value

def test_analyze_slow(detector, monitor):
    # High latency (threshold is 3.0)
    for _ in range(10): monitor.track_call("svc", 4.5, 200)
    
    result = detector.analyze_health("svc")
    assert result["state"] == HealthState.SLOW.value

def test_recommendation_circuit_breaker(detector, monitor):
    # Critical failure (60%) -> Circuit Breaker
    for _ in range(10): monitor.track_call("svc", 0.1, 500)
    rec = detector.recommend_pattern("svc")
    assert rec["pattern"] == "circuit_breaker"

def test_recommendation_retry(detector, monitor):
    # 40% failure rate with 503s (> 30 threshold) -> Retry
    for _ in range(6): monitor.track_call("svc", 0.1, 200)
    for _ in range(4): monitor.track_call("svc", 0.1, 503) 
    rec = detector.recommend_pattern("svc")
    assert rec["pattern"] == "retry"

def test_recommendation_timeout(detector, monitor):
    # Slow service (> 3.0 threshold) -> Timeout
    for _ in range(10): monitor.track_call("svc", 5.5, 200)
    rec = detector.recommend_pattern("svc")
    assert rec["pattern"] == "timeout"
