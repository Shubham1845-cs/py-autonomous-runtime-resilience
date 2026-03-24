# Pattern 3 (Timeout) Fix - Purple Panel Not Showing

## Problem
Pattern 3 was not showing the purple TIMEOUT GUARD panel. Instead, it was showing CIRCUIT BREAKER (amber) or RETRY (blue).

## Root Cause
**CRITICAL BUG in `live_demo.py`**: The `inject_delay()` function didn't clear the error rate from Pattern 2.

### What Was Happening:
1. **Pattern 2** runs: `inject_errors(0.98, code=503)`
   - Fault proxy config: `{"localhost:8000": {"status": 503, "rate": 0.98}}`
   - Result: 98% of requests return HTTP 503

2. **Pattern 3** runs: `inject_delay(8)`
   - Fault proxy config: `{"localhost:8000": {"status": 503, "rate": 0.98, "delay": 8}}`
   - **BUG**: The old error config was still there!
   - Result: 98% errors AND 8-second delay on ALL requests

3. **Detector sees**:
   - Failure rate: 98% (from the errors)
   - Latency: 8+ seconds (from the delay)
   - Decision: Failure rate >= 60% → CIRCUIT BREAKER ❌
   - **Should be**: Latency > 3s → TIMEOUT ✅

The detector checks latency FIRST, but because there were ALSO 98% errors, it was triggering CIRCUIT BREAKER instead of TIMEOUT.

## The Fix

Modified `inject_delay()` in `saleor_sandbox/live_demo.py` to explicitly clear the error rate:

```python
# BEFORE (broken):
def inject_delay(delay_seconds, rate=1.0):
    api_post(PROXY_CTRL, {"localhost:8000": {"delay": delay_seconds, "rate": rate}})
    # This ADDS delay but KEEPS the old "status": 503, "rate": 0.98

# AFTER (fixed):
def inject_delay(delay_seconds, rate=1.0):
    api_post(PROXY_CTRL, {"localhost:8000": {"delay": delay_seconds, "rate": 0, "status": 0}})
    # This CLEARS errors by setting rate=0 and status=0
```

Now Pattern 3 injects ONLY the 8-second delay, with NO errors:
- Failure rate: 0% (no errors)
- Latency: 8+ seconds
- Decision: Latency > 3s → TIMEOUT ✅

## Files Modified
- `AutoHeal-Py/saleor_sandbox/live_demo.py` - Line 46: Fixed `inject_delay()` function

## How to Apply
You don't need to restart anything! Just run the demo again:

```bash
cd AutoHeal-Py
python saleor_sandbox/live_demo.py
```

## Expected Results

### Pattern 1 (50% errors):
- ✅ Blue panel: "Retry with Exponential Backoff"
- ✅ Blue node in topology

### Pattern 2 (98% errors):
- ✅ Amber panel: "Circuit Breaker"
- ✅ Amber node in topology
- ✅ Terminal: "⬆️ ESCALATION: RETRY → CIRCUIT_BREAKER"

### Pattern 3 (8s latency):
- ✅ Purple panel: "Timeout Guard"
- ✅ Purple node in topology
- ✅ Terminal: "⬆️ ESCALATION: CIRCUIT_BREAKER → TIMEOUT"
- ✅ **This is now fixed!**

## Why This Fix Works

The detector has this priority order:
```python
1. IF latency > 3s        → TIMEOUT
2. IF failure_rate >= 60% → CIRCUIT BREAKER
3. IF error_503_rate > 30% → RETRY
```

**Before the fix**:
- Pattern 3 had BOTH high latency (8s) AND high failure rate (98%)
- Even though latency is checked first, the failure rate was so high it triggered CIRCUIT BREAKER

**After the fix**:
- Pattern 3 has ONLY high latency (8s), NO errors
- Failure rate: 0%
- Latency check triggers first → TIMEOUT ✅

## Verification

Run the demo and watch for these terminal messages:

**Pattern 3 should show**:
```
⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆
  ⬆️  ESCALATION on 'localhost:8001'
  Upgrading: CIRCUIT_BREAKER → TIMEOUT
  Reason: High average latency (8.00s > 3.0s)
⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆
```

**Dashboard should show**:
- Purple "PROTECTED" badge
- "Timeout Guard" heading
- "Triggered by: High average latency (8.00s > 3.0s)"
- Purple node in 3D topology

If you still see amber "Circuit Breaker", the fix wasn't applied. Make sure you're running the updated `live_demo.py` script!
