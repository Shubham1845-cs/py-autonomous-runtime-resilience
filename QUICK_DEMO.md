# Quick Demo — 5 Minute Setup

## Step 1: Start 3 Terminals

```bash
# Terminal 1
cd AutoHeal-Py
python saleor_sandbox/fault_proxy.py

# Terminal 2
cd AutoHeal-Py
python saleor_sandbox/runner.py

# Terminal 3
cd AutoHeal-Py
python webapp/app.py
```

## Step 2: Open Dashboard

Open in browser: **http://localhost:5000/dashboard**

## Step 3: Run Automated Demo

```bash
# Terminal 4
cd AutoHeal-Py
python saleor_sandbox/live_demo.py
```

Press ENTER at each prompt and watch the dashboard update live.

---

## What You'll See

1. **Healthy baseline** → Green service card, 0% failures
2. **50% errors injected** → Service turns yellow, RETRY pattern appears
3. **98% errors injected** → Service turns red, CIRCUIT BREAKER pattern appears
4. **8s latency injected** → TIMEOUT GUARD pattern appears
5. **Faults cleared** → Service returns to green, all patterns removed

**Total demo time:** ~3-4 minutes

---

## Key Points for Teacher

- No code changes in the application
- Agent makes all decisions autonomously
- Different failures trigger different patterns
- System self-heals when service recovers

---

## Troubleshooting

If something breaks:
```bash
python restart_demo.py
```
Then restart the 3 terminals.
