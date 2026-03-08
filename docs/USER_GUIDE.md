# AutoHeal-Py User Guide

Welcome to AutoHeal-Py, the autonomous self-healing framework for Python microservices.

## 🚀 Quick Start

### 1. Installation
```bash
pip install autoheal-py
```

### 2. Basic Setup
To protect your entire application, simply add these lines at your entry point (e.g., `main.py` or `app.py`):

```python
from autoheal import install_monitor, get_injector, create_agent
from autoheal.monitor import _monitor

# 1. Start monitoring all requests calls
install_monitor()

# 2. Create the autonomous agent
agent = create_agent(_monitor)

# 3. Start the healing loop
agent.start()
```

That's it! AutoHeal-Py will now autonomously monitor all outgoing HTTP calls and apply protection if services start failing.

## ⚙️ Configuration

You can customize the sensitivity of the agent:

```python
agent = create_agent(
    monitor,
    scan_interval=5.0,        # Scan every 5 seconds
    critical_threshold=50.0,  # Inject Circuit Breaker at 50% failure
    degraded_threshold=20.0,  # Inject Retry at 20% failure
    slow_threshold=3.0,       # Inject Timeout if calls take > 3s
    grace_period=300          # Keep patterns for 5 mins after recovery
)
```

## 📊 Using the Dashboard

AutoHeal-Py comes with a built-in Glassmorphism dashboard. To run it:

```bash
cd webapp
python app.py
```
Visit `http://localhost:5000` to see real-time health graphs, active injections, and a live event feed.

## 🛠️ Manual Decoration (Advanced)

If you want to protect specific functions (not just HTTP calls), use decorators:

```python
from autoheal import with_circuit_breaker, with_retry

@with_circuit_breaker(failure_threshold=5)
def my_custom_logic():
    # ... your code ...
    pass
```

## 🛡️ Patterns Supported

1.  **Circuit Breaker**: Stops traffic to a failing service to prevent cascading failures.
2.  **Retry**: Automatically retries transient failures with exponential backoff.
3.  **Timeout**: Prevents local resource exhaustion by cutting off slow requests.
