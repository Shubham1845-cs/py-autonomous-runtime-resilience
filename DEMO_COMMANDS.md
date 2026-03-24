# AutoHeal-Py Demo Commands

## Quick Start (3 Terminals)

### Terminal 1 — Fault Proxy
```bash
cd AutoHeal-Py
python saleor_sandbox/fault_proxy.py
```
Expected output: `[FaultProxy] Running on port 8001`

### Terminal 2 — Sidecar + Agent + Traffic
```bash
cd AutoHeal-Py
python saleor_sandbox/runner.py
```
Expected output:
- `[AutoHeal] ✅ Monitor installed successfully`
- `[Agent] 🚀 Started`
- Periodic scan output every 5 seconds

### Terminal 3 — Dashboard
```bash
cd AutoHeal-Py
python webapp/app.py
```
Expected output: `AutoHeal-Py Dashboard → http://localhost:5000`

Then open: **http://localhost:5000/dashboard**

---

## Fault Injection (Terminal 4)

### Method 1: Simple Python Script (Recommended)
```bash
cd AutoHeal-Py

# Inject 80% 503 errors → triggers Retry or Circuit Breaker
python inject_fault_simple.py error_storm

# Inject 6s latency → triggers Timeout Guard
python inject_fault_simple.py latency_spike

# Inject 50% 500 errors → triggers Circuit Breaker
python inject_fault_simple.py partial_outage

# Clear all faults
python inject_fault_simple.py clear
```

### Method 2: Original chaos_control.py
```bash
# 40% 503 errors on localhost:8001
python saleor_sandbox/chaos_control.py localhost:8001 status 503 0.4

# 70% 500 errors
python saleor_sandbox/chaos_control.py localhost:8001 status 500 0.7

# 5s delay on all requests
python saleor_sandbox/chaos_control.py localhost:8001 delay 5 1.0
```

---

## What to Watch

1. **Dashboard** (`http://localhost:5000/dashboard`):
   - Service card shows failure rate climbing
   - After ~10-15 seconds, agent injects a pattern
   - Pattern badge appears (Retry / Circuit Breaker / Timeout)
   - Event feed shows injection event

2. **Terminal 2** (runner):
   - Scan output every 5 seconds
   - When pattern injected: `🚨 ACTION: Injected [RETRY] on 'localhost:8001'`
   - When recovered: `✅ ACTION: Removed [RETRY] from 'localhost:8001' — RECOVERED!`

---

## Clean Restart

If things get messy:
```bash
cd AutoHeal-Py
python restart_demo.py
```

Then restart the 3 terminals manually.

---

## Explaining to Teacher

### 1. Start with Healthy State
Show the dashboard with green service card, 0% failure rate, no patterns.

### 2. Inject Error Storm
```bash
python inject_fault_simple.py error_storm
```
Say: "I'm simulating a service failure — 80% of requests now return HTTP 503."

### 3. Watch Agent React
Point to the dashboard:
- "Failure rate is climbing"
- "After a few scans, the agent detects CRITICAL state"
- "It autonomously injects a Circuit Breaker pattern"
- "No human intervention — the system healed itself"

### 4. Clear Fault and Show Recovery
```bash
python inject_fault_simple.py clear
```
Say: "The service is healthy again. After 30 seconds of stable health, the agent will automatically remove the pattern."

### 5. Key Points
- Zero code changes in the application
- Monitor works by monkey-patching `requests` library
- Agent scans every 2 seconds and makes autonomous decisions
- Patterns are injected/removed dynamically at runtime

---

## Troubleshooting

### No services appear on dashboard
- Check Terminal 2 is running (runner.py)
- Wait 10 seconds for traffic to start

### Faults don't trigger patterns
- Make sure you're injecting on `localhost:8001` (not 8000)
- Wait 15-20 seconds for enough failed calls to accumulate
- Check Terminal 2 for scan output

### Port already in use
```bash
python restart_demo.py
```

### Dashboard shows old data
- Refresh the browser (F5)
- Or use the "Reset Demo" button in the dashboard (if available)
