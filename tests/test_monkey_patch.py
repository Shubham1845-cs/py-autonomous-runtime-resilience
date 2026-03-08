import pytest
import requests
import time
from autoheal.monitor import _monitor, install_monitor, uninstall_monitor

def test_requests_monkey_patching():
    # 1. Ensure clean state
    uninstall_monitor()
    _monitor.clear_metrics()
    
    # 2. Install
    install_monitor()
    
    # 3. Make a call (use a nonexistent local or reliable external URL)
    # Use a try/except because we don't care about success, just that it's tracked
    url = "http://localhost:9999/nonexistent" 
    try:
        requests.get(url, timeout=0.1)
    except:
        pass
    
    # 4. Verify tracking
    services = _monitor.get_all_services()
    assert "localhost:9999" in services
    
    metrics = _monitor.get_metrics("localhost:9999")
    assert len(metrics) >= 1
    assert "duration" in metrics[0]
    
    # 5. Cleanup
    uninstall_monitor()
