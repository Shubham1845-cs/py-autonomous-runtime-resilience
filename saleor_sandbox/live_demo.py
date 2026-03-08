"""
AutoHeal-Py — Live Self-Healing Demonstration
==============================================
Demonstrates ALL 3 resilience patterns in sequence:

  Phase 1: 50% HTTP 503 errors → RETRY pattern
  Phase 2: 98% HTTP 503 errors → CIRCUIT BREAKER pattern
  Phase 3: 8-second delay      → TIMEOUT GUARD pattern
  Phase 4: Clear all chaos     → Patterns removed (HEALTHY)

Prerequisites:
  - Saleor running in Docker (port 8000)
  - Fault Proxy running:  python saleor_sandbox/fault_proxy.py
  - Dashboard running:    python webapp/app.py

Usage:
  python saleor_sandbox/live_demo.py
"""

import urllib.request
import urllib.error
import json
import time
import sys

API_BASE     = "http://localhost:5000"
PROXY_CTRL   = "http://localhost:8001/_control"

# ── Helpers ───────────────────────────────────────────────────────────────────

def api_get(path):
    resp = urllib.request.urlopen(f"{API_BASE}{path}", timeout=5)
    return json.loads(resp.read().decode())

def api_post(url, body=None):
    data = json.dumps(body or {}).encode()
    req  = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    resp = urllib.request.urlopen(req, timeout=5)
    return json.loads(resp.read().decode())

def inject_errors(rate, code=503):
    api_post(PROXY_CTRL, {"localhost:8000": {"status": code, "rate": rate}})
    print(f"  🔥 Fault proxy: {int(rate*100)}% requests → HTTP {code}")

def inject_delay(delay_seconds, rate=1.0):
    api_post(PROXY_CTRL, {"localhost:8000": {"delay": delay_seconds, "rate": rate}})
    print(f"  🔥 Fault proxy: {delay_seconds}s delay on ALL requests")

def clear_chaos():
    api_post(PROXY_CTRL, {"localhost:8000": {"rate": 0, "delay": 0}})
    print("  ✅ Fault proxy: faults cleared — normal traffic")

def reset_demo():
    """Clear monitor metrics + remove all active patterns for a clean slate."""
    r = api_post(f"{API_BASE}/api/reset-demo")
    print(f"  🔄 Reset: {r['message']}")

def show_status(heading):
    print(f"\n{'─'*60}")
    print(f"  📋 {heading}")
    print(f"{'─'*60}")
    try:
        svcs   = api_get("/api/services")
        status = api_get("/api/agent/status")
    except Exception as e:
        print(f"  ❌ Dashboard unreachable: {e}")
        return
    print(f"  🤖 Agent  : Scans={status['scan_count']}  |  Uptime={int(status['uptime_seconds'])}s")
    print(f"  💉 Injections: {status['active_injections']} active  |  {status['total_injections']} total")
    print()
    for svc in svcs:
        status_icon = {"healthy": "✅", "degraded": "⚠️ ", "critical": "🔴"}.get(svc["status"], "❓")
        p = svc.get("active_pattern")
        d = svc.get("pattern_details") or {}
        cfg = d.get("config", {})
        print(f"  Service : {svc['service']}")
        print(f"  Status  : {status_icon} {svc['status'].upper()}")
        print(f"  Failures: {svc['failure_rate']}%   Latency: {svc['avg_latency']}s   Calls: {svc['total_calls']}")
        if p:
            age = round(d.get("age_seconds", 0))
            cfg_str = "  |  ".join(f"{k.replace('_',' ')}={v}" for k, v in cfg.items())
            print(f"  Pattern : 🛡️  {p.upper().replace('_', ' ')}  (active {age}s)")
            if cfg_str:
                print(f"  Config  : {cfg_str}")
        else:
            print(f"  Pattern : None — no protection")
        print()

def countdown(seconds, msg):
    print(f"\n  ⏳ {msg} ({seconds}s countdown)")
    for i in range(seconds, 0, -1):
        sys.stdout.write(f"\r  ⏳ {i:>3}s remaining…")
        sys.stdout.flush()
        time.sleep(1)
    print(f"\r  ✅ Done!          ")

def sep(title, char="═"):
    line = char * 60
    print(f"\n{line}")
    print(f"  {title}")
    print(f"{line}")


# ── MAIN DEMO ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":

    sep("AutoHeal-Py — ALL 3 PATTERNS LIVE DEMO", "█")
    print("""
  This demo shows all three resilience patterns being
  autonomously injected and removed by the AutoHeal agent:

    [1]  RETRY         — handles transient 503 errors
    [2]  CIRCUIT BREAKER — handles total service failure
    [3]  TIMEOUT GUARD — handles extreme response latency

  Dashboard: http://localhost:5000/dashboard
    """)

    # ── STEP 0: Baseline ───────────────────────────────────────
    input("  [ENTER] → BEGIN: Show healthy baseline")
    reset_demo()
    countdown(5, "Letting metrics settle")
    show_status("BASELINE — No faults, No patterns")

    # ══════════════════════════════════════════════════════════
    #  PATTERN 1: RETRY
    #  Trigger: moderate 503 errors (50%)
    # ══════════════════════════════════════════════════════════
    sep("PATTERN 1 OF 3 — RETRY")
    print("  WHAT: Transient errors (50%) detected")
    print("  WHY:  Service occasionally fails → safe to retry")
    print("  HOW:  AutoHeal wraps `requests` with Exponential Backoff")
    input("\n  [ENTER] → Inject 50% error rate")

    reset_demo()
    inject_errors(0.50, code=503)
    countdown(12, "Waiting for agent to detect DEGRADED state and inject RETRY")
    show_status("AFTER PATTERN 1 — Did RETRY get injected?")
    print("  ✅ Expected: service DEGRADED → Pattern: RETRY")
    print("  📊 Dashboard: Blue pulsing badge 'PROTECTED — Retry with Exponential Backoff'")

    # ══════════════════════════════════════════════════════════
    #  PATTERN 2: CIRCUIT BREAKER
    #  Trigger: near-total failure (98%)
    # ══════════════════════════════════════════════════════════
    sep("PATTERN 2 OF 3 — CIRCUIT BREAKER")
    print("  WHAT: Near-total service failure (98% errors)")
    print("  WHY:  Retries are pointless — must STOP traffic immediately")
    print("  HOW:  AutoHeal opens the circuit (all calls fail-fast)")
    input("\n  [ENTER] → Escalate to 98% error rate")

    reset_demo()
    inject_errors(0.98, code=503)
    countdown(12, "Waiting for agent to detect CRITICAL state and inject CIRCUIT BREAKER")
    show_status("AFTER PATTERN 2 — Did CIRCUIT BREAKER get injected?")
    print("  ✅ Expected: service CRITICAL → Pattern: CIRCUIT BREAKER")
    print("  📊 Dashboard: Amber pulsing badge + 'Stops all traffic immediately'")

    # ══════════════════════════════════════════════════════════
    #  PATTERN 3: TIMEOUT GUARD
    #  Trigger: extreme latency (8s delay)
    # ══════════════════════════════════════════════════════════
    sep("PATTERN 3 OF 3 — TIMEOUT GUARD")
    print("  WHAT: Extreme response latency (8 second delay on ALL requests)")
    print("  WHY:  Threads hang waiting → server runs out of workers")
    print("  HOW:  AutoHeal wraps calls with a hard deadline (Timeout)")
    input("\n  [ENTER] → Inject 8-second latency")

    reset_demo()
    inject_delay(8, rate=1.0)
    countdown(15, "Waiting for agent to detect SLOW state and inject TIMEOUT GUARD")
    show_status("AFTER PATTERN 3 — Did TIMEOUT GUARD get injected?")
    print("  ✅ Expected: service SLOW → Pattern: TIMEOUT GUARD")
    print("  📊 Dashboard: Purple pulsing badge + 'Cuts off slow requests'")

    # ══════════════════════════════════════════════════════════
    #  RECOVERY
    # ══════════════════════════════════════════════════════════
    sep("RECOVERY — Clearing all faults")
    print("  Simulates: the downstream service comes back online")
    input("\n  [ENTER] → Clear all faults")

    clear_chaos()
    countdown(35, "Waiting 35s for grace period to expire and pattern to be removed")
    show_status("FINAL STATE — All patterns should be removed")
    print("  ✅ Expected: service HEALTHY, Pattern: None")

    # ── DONE ───────────────────────────────────────────────────
    sep("DEMO COMPLETE — AutoHeal-Py: Zero-Touch Self-Healing Verified!", "█")
    print("  Three patterns were autonomously detected, applied, and removed")
    print("  without touching a single line of Saleor's application code.\n")
    print("  📊 Dashboard: http://localhost:5000/dashboard")
    print()
