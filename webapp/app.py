from flask import Flask, render_template, jsonify, request
import sys
import os
import logging

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from autoheal.monitor import get_all_services, get_health_summary, get_metrics, _monitor, install_monitor
from autoheal.detector import create_detector
from autoheal.injector import PatternInjector
from autoheal.agent import AutoHealAgent

# ─── Activate monitor (patches requests.get/post/put/delete/patch) ──────────
install_monitor()


# ─── logging ───────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)

app = Flask(__name__)
app.config['SECRET_KEY'] = 'autoheal-secret-key-2024'

# ─── Framework instances ────────────────────────────────────────────────────
detector = create_detector(_monitor)
injector = PatternInjector()
agent    = AutoHealAgent(
    monitor   = _monitor,
    detector  = detector,
    injector  = injector,
    scan_interval_seconds = 5.0,
    grace_period_seconds  = 120,   # shorter grace for demo
)

# Start the autonomous agent in background when the Flask dev server starts
# (use 'before_first_request' pattern for production; here we start directly)
agent.start()

# ─── Demo Traffic Seeder ─────────────────────────────────────────────────────
# Simulates realistic HTTP traffic so the dashboard has live data without Saleor.
# Injects calls directly into _monitor (bypasses real network).
import threading, random, time as _time

_DEMO_SERVICES = {
    "payment-gateway": {"base_latency": 0.2, "fail_rate": 0.05},
    "inventory-service": {"base_latency": 0.1, "fail_rate": 0.02},
    "shipping-api":      {"base_latency": 0.35, "fail_rate": 0.08},
    "auth-service":      {"base_latency": 0.05, "fail_rate": 0.01},
}

def _seed_demo_traffic():
    while True:
        for svc, cfg in _DEMO_SERVICES.items():
            latency    = cfg["base_latency"] + random.uniform(-0.05, 0.2)
            is_failure = random.random() < cfg["fail_rate"]
            status     = random.choice([500, 503, 429]) if is_failure else 200
            error      = "connection refused" if status in (503, 500) else None
            _monitor.track_call(svc, max(0.01, latency), status, error)
        _time.sleep(1.5)

_seeder = threading.Thread(target=_seed_demo_traffic, daemon=True, name="demo-seeder")
_seeder.start()



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
    # annotate active patterns
    for s in summaries:
        s['active_pattern'] = injector.get_pattern_type(s['service'])
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
