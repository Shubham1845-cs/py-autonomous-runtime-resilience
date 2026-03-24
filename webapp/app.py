from flask import Flask, render_template, jsonify, request
import sys
import os
import logging
import threading
import time as _time_mod

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from autoheal.monitor import get_all_services, get_health_summary, get_metrics, _monitor, install_monitor
from autoheal.detector import create_detector
from autoheal.injector import PatternInjector
from autoheal.agent import AutoHealAgent

# ─── Activate monitor (patches requests.get/post/put/delete/patch) ──────────
install_monitor()


# ─── Chaos State ─────────────────────────────────────────────────────────────
class ChaosState:
    """Thread-safe singleton tracking the active fault injection mode."""
    _MODES = {
        "none":             {"label": "No Fault",          "icon": "fa-circle-check",      "color": "#10b981"},
        "error_storm":      {"label": "Error Storm",        "icon": "fa-bolt",              "color": "#ef4444"},
        "latency_spike":    {"label": "Latency Spike",      "icon": "fa-hourglass-half",    "color": "#f59e0b"},
        "connection_drop":  {"label": "Connection Drop",    "icon": "fa-plug-circle-xmark", "color": "#a855f7"},
        "partial_outage":   {"label": "Partial Outage (50%)","icon": "fa-cloud-bolt",      "color": "#3b82f6"},
    }

    def __init__(self):
        self._lock   = threading.Lock()
        self._mode:  str             = "none"
        self._since: "float | None" = None

    @property
    def mode(self):
        with self._lock:
            return self._mode

    def inject(self, mode: str):
        if mode not in self._MODES:
            raise ValueError(f"Unknown fault mode: {mode!r}")
        with self._lock:
            self._mode  = mode
            self._since = _time_mod.time()

    def clear(self):
        with self._lock:
            self._mode  = "none"
            self._since = None

    def status(self) -> dict:
        with self._lock:
            meta = self._MODES.get(self._mode, self._MODES["none"])
            age  = round(_time_mod.time() - self._since) if isinstance(self._since, float) else 0
            return {
                "mode":     self._mode,
                "active":   self._mode != "none",
                "label":    meta["label"],
                "icon":     meta["icon"],
                "color":    meta["color"],
                "age_seconds": age,
                "modes":    {
                    k: {"label": v["label"], "icon": v["icon"], "color": v["color"]}
                    for k, v in self._MODES.items() if k != "none"
                },
            }


_chaos = ChaosState()


# ─── logging ───────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)

app = Flask(__name__)
app.config['SECRET_KEY'] = 'autoheal-secret-key-2024'

# ─── Framework instances ────────────────────────────────────────────────────
# Thresholds tuned for live_demo.py:
#   Pattern 1: 50% errors  → DEGRADED (10-60%) → RETRY
#   Pattern 2: 98% errors  → CRITICAL (60%+)   → CIRCUIT BREAKER
#   Pattern 3: 8s latency  → SLOW (>3s)        → TIMEOUT
detector = create_detector(_monitor,
    critical_failure_threshold = 60.0,   # CRITICAL at 60%+ failures (for Pattern 2)
    degraded_failure_threshold = 10.0,   # DEGRADED at 10%+ failures (for Pattern 1)
    slow_latency_threshold     = 3.0,    # SLOW at 3s+ latency (for Pattern 3)
)
injector = PatternInjector()
agent    = AutoHealAgent(
    monitor   = _monitor,
    detector  = detector,
    injector  = injector,
    scan_interval_seconds = 2.0,   # scan every 2s for fast demo response
    grace_period_seconds  = 30,    # remove pattern 30s after recovery
)

# Start the autonomous agent in background when the Flask dev server starts
# (use 'before_first_request' pattern for production; here we start directly)
agent.start()

# ─── Saleor Live Traffic Generator ───────────────────────────────────────────
# Sends real GraphQL requests to Saleor through the fault proxy.
# Because install_monitor() was called above, these requests are automatically
# tracked by _monitor, which allows the agent to detect faults and self-heal.
import threading, random, time as _time, requests as _requests

SALEOR_PROXY_URL = "http://localhost:8001/graphql/"
SALEOR_TARGET_URL = "http://localhost:8000/graphql/"

_SALEOR_QUERIES = [
    '{ shop { name } }',
    '{ products(first: 5, channel: "default-channel") { edges { node { name } } } }',
    '{ categories(first: 5) { edges { node { name } } } }',
]

def _saleor_traffic_loop():
    """Send real traffic to Saleor through the fault proxy.
    
    Applies chaos faults BEFORE the request so the monitor tracks real failures:
      • error_storm      → force HTTP 503 by pointing at an unreachable port
      • latency_spike    → sleep 4-8s before sending (triggers timeout detection)
      • connection_drop  → raise a ConnectionError (tracked as error by monitor)
      • partial_outage   → 50 % chance of connection error
    """
    _time.sleep(3)  # wait for Flask to start
    print("[TrafficGen] Starting live Saleor traffic through fault proxy...")
    while True:
        mode  = _chaos.mode
        query = random.choice(_SALEOR_QUERIES)
        try:
            # ── Apply pre-request chaos ──────────────────────────────────
            if mode == "latency_spike":
                _time.sleep(random.uniform(4.0, 8.0))  # artificial delay

            if mode == "connection_drop":
                raise _requests.exceptions.ConnectionError("[chaos] connection forcibly dropped")

            if mode == "partial_outage" and random.random() < 0.55:
                raise _requests.exceptions.ConnectionError("[chaos] partial outage")

            # Use a dead port for error_storm so the TCP connect fails fast
            target_url = SALEOR_PROXY_URL if mode != "error_storm" else "http://localhost:19998/graphql/"

            _requests.post(
                target_url,
                json={"query": query},
                headers={"X-Target-URL": SALEOR_TARGET_URL},
                timeout=10,
            )
        except Exception:
            pass  # monitor tracks the failure automatically
        _time.sleep(0.8)

_traffic_thread = threading.Thread(target=_saleor_traffic_loop, daemon=True, name="saleor-traffic")
_traffic_thread.start()



# ─── Page routes ────────────────────────────────────────────────────────────

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

@app.route('/monitor')
def monitor_page():
    return render_template('monitor.html')

@app.route('/patterns')
def patterns():
    return render_template('patterns.html')

@app.route('/docs')
def docs():
    return render_template('docs.html')

@app.route('/settings')
def settings():
    return render_template('settings.html')

# ─── API: Services ──────────────────────────────────────────────────────────

@app.route('/api/services')
def api_services():
    """All monitored services with health summaries."""
    services  = get_all_services()
    summaries = [get_health_summary(s) for s in services]
    # annotate active patterns with full details
    for s in summaries:
        s['active_pattern'] = injector.get_pattern_type(s['service'])
        active_record = injector.get_active(s['service'])
        if active_record:
            s['pattern_details'] = active_record.to_dict()
        else:
            s['pattern_details'] = None
    return jsonify(summaries)

@app.route('/api/service/<service_name>')
def api_service_detail(service_name):
    """Detailed metrics + recommendation + injection status for one service."""
    metrics        = get_metrics(service_name, window_seconds=300)
    summary        = get_health_summary(service_name)
    recommendation = detector.recommend_pattern(service_name)
    active_record  = injector.get_active(service_name)

    return jsonify({
        "summary":        summary,
        "metrics":        metrics[-50:],    # last 50 calls
        "recommendation": recommendation,
        "active_pattern": active_record.to_dict() if active_record else None,
    })

# ─── API: Stats ─────────────────────────────────────────────────────────────

@app.route('/api/stats')
def api_stats():
    """Global statistics for the home page hero + dashboard bar."""
    services = get_all_services()

    if not services:
        return jsonify({
            "total_services":  0,
            "total_calls":     0,
            "active_patterns": 0,
            "system_status":   "No Data",
            "healthy_count":   0,
            "degraded_count":  0,
            "critical_count":  0,
        })

    summaries    = [get_health_summary(s) for s in services]
    total_calls  = sum(s['total_calls'] for s in summaries)
    healthy      = sum(1 for s in summaries if s['status'] == 'healthy')
    degraded     = sum(1 for s in summaries if s['status'] == 'degraded')
    critical     = sum(1 for s in summaries if s['status'] == 'critical')

    if critical > 0:
        system_status = "Critical"
    elif degraded > 0:
        system_status = "Degraded"
    else:
        system_status = "Healthy"

    return jsonify({
        "total_services":  len(services),
        "total_calls":     total_calls,
        "active_patterns": injector.active_count(),
        "system_status":   system_status,
        "healthy_count":   healthy,
        "degraded_count":  degraded,
        "critical_count":  critical,
    })

# ─── API: Agent ─────────────────────────────────────────────────────────────

@app.route('/api/agent/status')
def api_agent_status():
    """AutoHeal Agent runtime status (scan count, active patterns, uptime)."""
    return jsonify(agent.get_status())

@app.route('/api/agent/events')
def api_agent_events():
    """Recent agent events (pattern injections/removals/scans)."""
    limit = request.args.get('limit', 30, type=int)
    return jsonify(agent.get_events(limit=limit))

@app.route('/api/injector/summary')
def api_injector_summary():
    """Current injector state: active injections + full history."""
    return jsonify(injector.summary())

@app.route('/api/reset-demo', methods=['POST'])
def api_reset_demo():
    """Remove all active pattern injections for a clean demo phase.
    NOTE: we do NOT clear metrics so the service card stays visible on the dashboard.
    The short 15s analysis window means fresh chaos data will dominate within one scan cycle."""
    active = injector.get_all_active()
    for record in active:
        try:
            injector.remove(record.service_name)
        except Exception:
            pass
    return jsonify({"status": "reset", "cleared": len(active), "message": "Patterns removed — metrics preserved"})


# ─── API: Chaos Control ──────────────────────────────────────────────────────

@app.route('/api/chaos', methods=['GET'])
def api_chaos_status():
    """Return current chaos fault injection status."""
    return jsonify(_chaos.status())


@app.route('/api/chaos', methods=['POST'])
def api_chaos_inject():
    """Activate a fault mode: POST {"mode": "error_storm"}"""
    body = request.get_json(force=True, silent=True) or {}
    mode = body.get("mode", "")
    try:
        _chaos.inject(mode)
        return jsonify({"ok": True, "mode": mode, "message": f"Fault '{mode}' injected — agent will respond shortly"})
    except ValueError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400


@app.route('/api/chaos', methods=['DELETE'])
def api_chaos_clear():
    """Clear all active fault injection."""
    _chaos.clear()
    return jsonify({"ok": True, "message": "Chaos cleared — service returning to normal"})

# ─── API: Patterns info ─────────────────────────────────────────────────────

@app.route('/api/patterns/info')
def api_patterns_info():
    return jsonify({
        "circuit_breaker": {
            "name":        "Circuit Breaker",
            "description": "Prevents cascading failures by failing fast when a service is unhealthy",
            "states":      ["CLOSED", "OPEN", "HALF_OPEN"],
            "use_case":    "High failure rates (>50%)"
        },
        "retry": {
            "name":        "Retry with Exponential Backoff",
            "description": "Automatically retries failed requests with increasing delays",
            "algorithm":   "2^attempt (1s, 2s, 4s…)",
            "use_case":    "Transient failures, 503 errors"
        },
        "timeout": {
            "name":        "Timeout Guard",
            "description": "Enforces maximum wait time for service calls",
            "mechanism":   "Thread-based timeout",
            "use_case":    "High latency (>3s)"
        }
    })

# ─── Entry point ────────────────────────────────────────────────────────────

if __name__ == '__main__':
    print("=" * 55)
    print("  AutoHeal-Py Dashboard")
    print("  → http://localhost:5000")
    print("  Agent scanning every 5s…")
    print("=" * 55)
    app.run(debug=True, host='0.0.0.0', port=5000, use_reloader=False)
