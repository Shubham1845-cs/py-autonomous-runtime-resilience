import pytest
import requests
from autoheal.injector import PatternInjector

def test_inject_circuit_breaker(injector):
    def test_func(): return "ok"
    
    # Inject
    wrapped = injector.inject("svc", test_func, "circuit_breaker", {"failure_threshold": 3})
    assert injector.has_pattern("svc")
    assert wrapped != test_func
    assert wrapped() == "ok"
    
    # Summary
    summary = injector.summary()
    assert summary["active_injections"] == 1
    assert summary["services"][0]["service"] == "svc"
    assert summary["services"][0]["pattern"] == "circuit_breaker"

def test_remove_injection(injector):
    def test_func(): return "ok"
    injector.inject("svc", test_func, "retry", {"max_attempts": 2})
    assert injector.has_pattern("svc")
    
    injector.remove("svc")
    assert not injector.has_pattern("svc")
    assert injector.active_count() == 0

def test_decorator_circuit_breaker():
    from autoheal.injector import with_circuit_breaker
    
    @with_circuit_breaker(failure_threshold=2)
    def decorated_func():
        return "ok"
    
    # Wrapper exposes property
    assert hasattr(decorated_func, "_circuit_breaker")
    assert decorated_func() == "ok"

def test_decorator_retry():
    from autoheal.injector import with_retry
    
    @with_retry(max_attempts=2)
    def decorated_func():
        return "ok"
    
    assert hasattr(decorated_func, "_retry")
    assert decorated_func() == "ok"

def test_decorator_timeout():
    from autoheal.injector import with_timeout
    
    @with_timeout(max_seconds=1.0)
    def decorated_func():
        return "ok"
    
    assert hasattr(decorated_func, "_timeout")
    assert decorated_func() == "ok"

def test_history_and_audit(injector):
    def test_func(): return "ok"
    injector.inject("svc", test_func, "timeout", {"max_seconds": 1.0})
    injector.remove("svc")
    
    history = injector.get_history()
    assert len(history) == 1
    assert history[0].service_name == "svc"
    assert history[0].removed_at is not None
