import pytest
import time
from autoheal.monitor import TelemetryMonitor
from autoheal.agent import AutoHealAgent, AgentEvent
from autoheal.detector import HealthDetector
from autoheal.injector import PatternInjector
from autoheal.monitor import uninstall_monitor, _monitor

@pytest.fixture(autouse=True)
def cleanup():
    # Ensure a clean state for the requests library and global monitor
    uninstall_monitor()
    _monitor.clear_metrics()
    yield
    uninstall_monitor()
    _monitor.clear_metrics()

@pytest.fixture
def test_env():
    monitor = TelemetryMonitor(window_seconds=60)
    detector = HealthDetector(monitor)
    injector = PatternInjector()
    agent = AutoHealAgent(monitor, detector, injector, scan_interval_seconds=1)
    return monitor, detector, injector, agent

def test_agent_orchestration_retry(test_env):
    monitor, detector, injector, agent = test_env
    svc = "test-service"
    
    # 1. Simulate 40% failures (503s)
    # Total 10 calls: 6 OK, 4 Fail (503)
    for _ in range(6): monitor.track_call(svc, 0.1, 200)
    for _ in range(4): monitor.track_call(svc, 0.1, 503)
    
    # 2. Run scan
    agent._scan_all_services()
    
    # 3. Assertions
    assert injector.has_pattern(svc)
    assert injector.get_pattern_type(svc) == "retry"
    
    events = agent.get_events()
    assert any(e["event"] == AgentEvent.PATTERN_INJECTED and e["service"] == svc for e in events)

def test_agent_orchestration_circuit_breaker(test_env):
    monitor, detector, injector, agent = test_env
    svc = "test-service"
    
    # 1. Simulate 60% failures (Critical)
    for _ in range(4): monitor.track_call(svc, 0.1, 200)
    for _ in range(6): monitor.track_call(svc, 0.1, 500)
    
    # 2. Run scan
    agent._scan_all_services()
    
    # 3. Assertions
    assert injector.has_pattern(svc)
    assert injector.get_pattern_type(svc) == "circuit_breaker"

def test_agent_orchestration_timeout(test_env):
    monitor, detector, injector, agent = test_env
    svc = "test-service"
    
    # 1. Simulate high latency (> 3.0s)
    for _ in range(10): monitor.track_call(svc, 4.5, 200)
    
    # 2. Run scan
    agent._scan_all_services()
    
    # 3. Assertions
    assert injector.has_pattern(svc)
    assert injector.get_pattern_type(svc) == "timeout"

def test_agent_auto_recovery(test_env):
    monitor, detector, injector, agent = test_env
    svc = "recovery-test-service"
    
    # 1. Inject pattern
    for _ in range(10): monitor.track_call(svc, 0.1, 500)
    agent._scan_all_services()
    assert injector.has_pattern(svc)
    
    # 2. Clear and simulate health
    monitor.clear_metrics(svc)
    # Populate grace period with health
    # Use 10s for stability. Detection requires min 5 calls (default).
    agent.grace_period = 10 
    
    # Add healthy calls (30 calls over a 10s window is plenty)
    for _ in range(30): monitor.track_call(svc, 0.1, 200)
    
    # Small sleep to ensure time advances for the detector's window
    time.sleep(1)
    
    # detector.should_remove_pattern uses analyze_health(svc, grace_period_seconds)
    # The metrics we just added have current timestamps.
    
    agent._scan_all_services()
    assert not injector.has_pattern(svc)
    
    events = agent.get_events()
    assert any(e["event"] == AgentEvent.PATTERN_REMOVED and e["service"] == svc for e in events)
