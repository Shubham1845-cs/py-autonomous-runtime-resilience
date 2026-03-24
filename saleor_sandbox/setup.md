# AutoHeal-Py Saleor Sandbox Demo Guide

Follow these steps to experience autonomous self-healing in a production-grade environment.

## 1. Prerequisites
- Docker & Saleor Platform running (Already done)
- Saleor API should be at `http://localhost:8000/graphql/`

## 2. Start the Sandbox Components
Open 3 separate terminals in `d:\Projects\AutoHeal-Py`:

### Terminal 1: The Fault Injection Proxy
This proxy sits between the load generator and Saleor to inject chaos.
```bash
python saleor_sandbox/fault_proxy.py
```

### Terminal 2: The AutoHeal Sidecar (Load + Monitor + Agent)
This process generates traffic to Saleor *through* the proxy and autonomously heals failures.
```bash
python saleor_sandbox/runner.py
```

### Terminal 3: The Dashboard
Run the dashboard to visualize everything.
```bash
cd webapp
python app.py
```

---

## 3. Experience the Self-Healing

### Scenario: Payment/API Gateway Failure
In a new terminal (Terminal 4), inject 503 Service Unavailable errors into 60% of Saleor requests:
```bash
python saleor_sandbox/chaos_control.py localhost:8000 status 503 0.6
```

**What to watch:**
1. **Dashboard (http://localhost:5000):** You'll see the `localhost:8000` service failure rate climb.
2. **AutoHeal Agent:** After ~10 seconds, it will detect the 503s and inject the **Retry** or **Circuit Breaker** pattern.
3. **Healing:** Once injected, you'll see "Injected" events in the Dashboard feed. The failed requests will be retried (self-healing) or cut off (fail-fast) depending on the pattern.

### Scenario: Network Latency Spike
Inject an 8-second delay into all requests:
```bash
python saleor_sandbox/chaos_control.py localhost:8000 delay 8 1.0
```

**What to watch:**
1. **Dashboard:** Average latency will spike to 8s.
2. **AutoHeal Agent:** Detects excessive latency and injects a **Timeout Guard**.
3. **Healing:** Requests will now fail-fast at 4-5s instead of hanging Saleor workers for 8s.

---

## 4. Analyze Results
After running the demo, generate the final report:
```bash
python saleor_sandbox/report.py
```
