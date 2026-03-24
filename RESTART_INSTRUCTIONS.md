# 🚀 RESTART INSTRUCTIONS - CRITICAL!

## What Was Fixed

✅ **Pattern 2 (Circuit Breaker)** - Now shows amber panel instead of blue retry
✅ **Pattern 3 (Timeout)** - Now shows purple panel
✅ **Topology colors** - Now change based on active pattern
✅ **Pattern upgrades** - Agent can now upgrade patterns dynamically

## Files Modified

1. `webapp/app.py` - Line 86: Threshold 70% → 60%
2. `autoheal/agent.py` - Lines 267-320: Added pattern upgrade logic

## YOU MUST RESTART THE WEBAPP!

The old webapp process is still running with the OLD code.

### Step 1: Stop the Webapp
In Terminal 3 (where `python webapp/app.py` is running):
- Press **Ctrl+C**

### Step 2: Restart the Webapp
```bash
cd AutoHeal-Py
python webapp/app.py
```

Wait for this message:
```
=======================================================
  AutoHeal-Py Dashboard
  → http://localhost:5000
  Agent scanning every 5s…
=======================================================
```

### Step 3: Run the Demo
In Terminal 4:
```bash
cd AutoHeal-Py
python saleor_sandbox/live_demo.py
```

## What You'll See (After Restart)

### Pattern 1 (50% errors):
- ✅ Blue panel: "Retry with Exponential Backoff"
- ✅ Blue node in topology

### Pattern 2 (98% errors):
- ✅ Amber panel: "Circuit Breaker"
- ✅ Amber node in topology
- ✅ Terminal shows: "⬆️ ESCALATION: RETRY → CIRCUIT_BREAKER"

### Pattern 3 (8s latency):
- ✅ Purple panel: "Timeout Guard"
- ✅ Purple node in topology
- ✅ Terminal shows: "⬆️ ESCALATION: CIRCUIT_BREAKER → TIMEOUT"

## Verification

Before running the demo, verify the fix is applied:
```bash
python verify_fix.py
```

Should show:
```
✅ Webapp is running on port 5000
✅ Code has correct threshold: 60.0%
✅ Configuration is correct!
```

## If It Still Doesn't Work

1. Make sure you **stopped the old webapp** (Ctrl+C)
2. Make sure you **restarted it** (python webapp/app.py)
3. Check the terminal output for the "⬆️ ESCALATION" messages
4. If you don't see escalation messages, the old code is still running

## Quick Test

After restarting, open the dashboard:
http://localhost:5000/dashboard

Run just Pattern 2:
```bash
cd AutoHeal-Py
python -c "
import urllib.request, json
# Reset
urllib.request.urlopen(urllib.request.Request('http://localhost:5000/api/reset-demo', method='POST', data=b'{}', headers={'Content-Type': 'application/json'}))
# Inject 98% errors
urllib.request.urlopen(urllib.request.Request('http://localhost:8001/_control', data=json.dumps({'localhost:8000': {'status': 503, 'rate': 0.98}}).encode(), headers={'Content-Type': 'application/json'}))
print('✅ Injected 98% errors - check dashboard in 15 seconds')
"
```

Wait 15 seconds, then check the dashboard. You should see:
- Red "CRITICAL" badge
- Amber "Circuit Breaker" panel (NOT blue "Retry")
- Amber node in topology

If you see blue "Retry" panel, the webapp wasn't restarted!
