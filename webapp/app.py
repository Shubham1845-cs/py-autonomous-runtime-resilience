

from flask import Flask, render_template, jsonify, request
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from autoheal.monitor import get_all_services, get_health_summary, get_metrics, _monitor
from autoheal.detector import create_detector

app = Flask(__name__)
app.config['SECRET_KEY'] = 'autoheal-secret-key-2024'

# Initialize detector
detector = create_detector(_monitor)

# ============ ROUTES ============

@app.route('/')
def index():
    """Landing page"""
    return render_template('index.html')

@app.route('/dashboard')
def dashboard():
    """Main dashboard - real-time monitoring"""
    return render_template('dashboard.html')

@app.route('/monitor')
def monitor():
    """Detailed telemetry monitoring page"""
    return render_template('monitor.html')

@app.route('/patterns')
def patterns():
    """Resilience patterns showcase"""
    return render_template('patterns.html')

@app.route('/docs')
def docs():
    """Documentation and API reference"""
    return render_template('docs.html')

@app.route('/settings')
def settings():
    """Configuration and settings"""
    return render_template('settings.html')

# ============ API ENDPOINTS ============

@app.route('/api/services')
def api_services():
    """Get all monitored services with health summaries"""
    services = get_all_services()
    summaries = [get_health_summary(s) for s in services]
    return jsonify(summaries)

@app.route('/api/service/<service_name>')
def api_service_detail(service_name):
    """Get detailed metrics for a specific service"""
    metrics = get_metrics(service_name, window_seconds=300)  # Last 5 minutes
    summary = get_health_summary(service_name)
    recommendation = detector.recommend_pattern(service_name)
    
    return jsonify({
        "summary": summary,
        "metrics": metrics,
        "recommendation": recommendation
    })

@app.route('/api/stats')
def api_stats():
    """Get global statistics"""
    services = get_all_services()
    
    if not services:
        return jsonify({
            "total_services": 0,
            "total_calls": 0,
            "active_patterns": 0,
            "system_status": "No Data",
            "healthy_count": 0,
            "degraded_count": 0,
            "critical_count": 0
        })
    
    summaries = [get_health_summary(s) for s in services]
    total_calls = sum(s['total_calls'] for s in summaries)
    
    # Count services by status
    healthy = sum(1 for s in summaries if s['status'] == 'healthy')
    degraded = sum(1 for s in summaries if s['status'] == 'degraded')
    critical = sum(1 for s in summaries if s['status'] == 'critical')
    
    # Determine overall system status
    if critical > 0:
        system_status = "Critical"
    elif degraded > 0:
        system_status = "Degraded"
    else:
        system_status = "Healthy"
    
    return jsonify({
        "total_services": len(services),
        "total_calls": total_calls,
        "active_patterns": 0,  # TODO: Track active patterns
        "system_status": system_status,
        "healthy_count": healthy,
        "degraded_count": degraded,
        "critical_count": critical
    })

@app.route('/api/patterns/info')
def api_patterns_info():
    """Get information about available resilience patterns"""
    return jsonify({
        "circuit_breaker": {
            "name": "Circuit Breaker",
            "description": "Prevents cascading failures by failing fast when a service is unhealthy",
            "states": ["CLOSED", "OPEN", "HALF_OPEN"],
            "use_case": "High failure rates (>50%)"
        },
        "retry": {
            "name": "Retry with Exponential Backoff",
            "description": "Automatically retries failed requests with increasing delays",
            "algorithm": "2^attempt (1s, 2s, 4s...)",
            "use_case": "Transient failures, 503 errors"
        },
        "timeout": {
            "name": "Timeout Guard",
            "description": "Enforces maximum wait time for service calls",
            "mechanism": "Thread-based timeout",
            "use_case": "High latency (>3s)"
        }
    })

if __name__ == '__main__':
    print(" AutoHeal-Py Dashboard starting...")
    print(" Dashboard: http://localhost:5000")
    print(" Monitor: http://localhost:5000/monitor")
    print(" Patterns: http://localhost:5000/patterns")
    app.run(debug=True, host='0.0.0.0', port=5000)
