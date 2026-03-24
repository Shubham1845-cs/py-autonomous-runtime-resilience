# AutoHeal-Py Live Demo Guide

This guide shows you how to run the **fully automated** live demonstration that showcases all 3 resilience patterns.

---

## What the Live Demo Does

The `live_demo.py` script is an **interactive, automated demonstration** that:

1. **Shows healthy baseline** — service running normally
2. **Injects 50% 503 errors** → Agent detects DEGRADED and injects **RETRY** pattern
3. **Escalates to 98% errors** → Agent detects CRITICAL and injects **CIRCUIT BREAKER** pattern
4. **Injects 8-second latency** → Agent detects SLOW and injects **TIMEOUT GUARD** pattern
5. **Clears all faults** → Agent detects recovery and removes all patterns

Each phase is interactive — you press ENTER to proceed, and the script shows you exactly what's happening at each step.

---

## Prerequisites

You need **3 terminals** running these processes:

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
- Periodic scan messages

### Terminal 3 — Dashboard
```bash
cd AutoHeal-Py
python webapp/app.py
```
Expected output: `AutoHeal-Py Dashboard → http://localhost:5000`

**Open the dashboard in your browser:** `http://localhost:5000/dashboard`

---

## Running the Live Demo

### Terminal 4 — Run the Demo Script
```bash
cd AutoHeal-Py
python saleor_sandbox/live_demo.py
```

---

## What You'll See

### Phase 0: Baseline
```
[ENTER] → BEGIN: Show healthy baseline
```
- Script resets all patterns
- Shows service status: HEALTHY, 0% failures
- Dashboard shows green service card

### Phase 1: RETRY Pattern
```
PATTERN 1 OF 3 — RETRY
[ENTER] → Inject 50% error rate
```
- Script injects 50% HTTP 503 errors
- Waits 12 seconds for agent to detect
- Shows service status: DEGRADED
- **Expected result:** Agent injects RETRY pattern
- Dashboard shows service card turn yellow/orange with "RETRY" badge

### Phase 2: CIRCUIT BREAKER Pattern
```
PATTERN 2 OF 3 — CIRCUIT BREAKER
[ENTER] → Escalate to 98% error rate
```
- Script escalates to 98% HTTP 503 errors
- Waits 12 seconds for agent to detect
- Shows service status: CRITICAL
- **Expected result:** Agent injects CIRCUIT BREAKER pattern
- Dashboard shows service card turn red with "CIRCUIT BREAKER" badge

### Phase 3: TIMEOUT GUARD Pattern
```
PATTERN 3 OF 3 — TIMEOUT GUARD
[ENTER] → Inject 8-second latency
```
- Script injects 8-second delay on all requests
- Waits 15 seconds for agent to detect
- Shows service status: SLOW
- **Expected result:** Agent injects TIMEOUT GUARD pattern
- Dashboard shows service card with "TIMEOUT" badge

### Phase 4: Recovery
```
RECOVERY — Clearing all faults
[ENTER] → Clear all faults
```
- Script clears all faults
- Waits 35 seconds for grace period
- Shows service status: HEALTHY
- **Expected result:** Agent removes all patterns
- Dashboard shows green service card with no patterns

---

## Demo Output Example

```
████████████████████████████████████████████████████████████
  AutoHeal-Py — ALL 3 PATTERNS LIVE DEMO
████████████████████████████████████████████████████████████

  This demo shows all three resilience patterns being
  autonomously injected and removed by the AutoHeal agent:

    [1]  RETRY         — handles transient 503 errors
    [2]  CIRCUIT BREAKER — handles total service failure
    [3]  TIMEOUT GUARD — handles extreme response latency

  Dashboard: http://localhost:5000/dashboard

  [ENTER] → BEGIN: Show healthy baseline

  🔄 Reset: Patterns removed — metrics preserved
  ⏳ Letting metrics settle (5s countdown)
  ⏳   5s remaining…
  ✅ Done!

────────────────────────────────────────────────────────────
  📋 BASELINE — No faults, No patterns
────────────────────────────────────────────────────────────
  🤖 Agent  : Scans=45  |  Uptime=90s
  💉 Injections: 0 active  |  3 total

  Service : localhost:8001
  Status  : ✅ HEALTHY
  Failures: 0.0%   Latency: 2.1s   Calls: 18
  Pattern : None — no protection

════════════════════════════════════════════════════════════
  PATTERN 1 OF 3 — RETRY
════════════════════════════════════════════════════════════
  WHAT: Transient errors (50%) detected
  WHY:  Service occasionally fails → safe to retry
  HOW:  AutoHeal wraps `requests` with Exponential Backoff

  [ENTER] → Inject 50% error rate

  🔥 Fault proxy: 50% requests → HTTP 503
  ⏳ Waiting for agent to detect DEGRADED state and inject RETRY (12s countdown)
  ⏳  12s remaining…
  ✅ Done!

────────────────────────────────────────────────────────────
  📋 AFTER PATTERN 1 — Did RETRY get injected?
────────────────────────────────────────────────────────────
  🤖 Agent  : Scans=52  |  Uptime=104s
  💉 Injections: 1 active  |  4 total

  Service : localhost:8001
  Status  : ⚠️  DEGRADED
  Failures: 52.3%   Latency: 2.2s   Calls: 22
  Pattern : 🛡️  RETRY  (active 8s)
  Config  : max attempts=3  |  backoff base=2  |  max delay=10  |  jitter=True

  ✅ Expected: service DEGRADED → Pattern: RETRY
  📊 Dashboard: Blue pulsing badge 'PROTECTED — Retry with Exponential Backoff'
```

---

## Explaining to Your Teacher

### What to Say at Each Phase

**Phase 1 (RETRY):**
> "I'm injecting 50% errors to simulate a service that's occasionally failing. Watch the dashboard — the failure rate is climbing. After a few scans, the agent detects this is DEGRADED and automatically injects a Retry pattern with exponential backoff. No human told it to do this."

**Phase 2 (CIRCUIT BREAKER):**
> "Now I'm escalating to 98% failures — the service is almost completely down. Retrying is pointless at this level. Watch — the agent detects CRITICAL state and switches to a Circuit Breaker. It opens the circuit and stops all traffic immediately to protect the rest of the system."

**Phase 3 (TIMEOUT GUARD):**
> "This time I'm injecting extreme latency — 8 seconds per request. This would normally hang all your worker threads. The agent detects the SLOW state and injects a Timeout Guard that cuts off requests after a few seconds."

**Phase 4 (RECOVERY):**
> "Now I'm clearing all faults — the service is healthy again. The agent monitors this for 30 seconds to make sure it's stable, then automatically removes all the patterns. The system healed itself completely."

### Key Points to Emphasize

1. **Zero code changes** — the application code was never touched
2. **Autonomous decisions** — the agent made all decisions based on metrics
3. **Pattern selection** — different failure signatures trigger different patterns
4. **Self-recovery** — patterns are removed automatically when health returns

---

## Troubleshooting

### "Dashboard unreachable" error
- Make sure Terminal 3 (webapp) is running
- Check `http://localhost:5000` is accessible

### No pattern gets injected
- Wait longer — agent scans every 2 seconds but needs multiple scans to confirm
- Check Terminal 2 (runner) is generating traffic
- Verify fault proxy (Terminal 1) is running

### Script hangs or errors
- Press Ctrl+C to stop
- Run `python restart_demo.py` to clean up
- Restart all 3 terminals

---

## Quick Commands Reference

```bash
# Start all 3 processes (in separate terminals)
python saleor_sandbox/fault_proxy.py
python saleor_sandbox/runner.py
python webapp/app.py

# Run the automated demo (Terminal 4)
python saleor_sandbox/live_demo.py

# Clean restart if needed
python restart_demo.py
```

---

## Manual Fault Injection (Alternative)

If you want to inject faults manually instead of using the automated script:

```bash
# 50% 503 errors
python inject_fault_simple.py error_storm

# 6s latency
python inject_fault_simple.py latency_spike

# 50% 500 errors
python inject_fault_simple.py partial_outage

# Clear all faults
python inject_fault_simple.py clear
```

Then watch the dashboard to see the agent react.
