# AutoHeal-Py Workflow Guide

This is the canonical onboarding document for understanding and running the project workflow end to end.

If you need a short faculty-facing summary, use docs/TEACHER_PROJECT_BRIEF.md.

## 1. What This Project Does

AutoHeal-Py is a runtime self-healing framework for Python services.

It works as a continuous loop:

1. Monitor outgoing HTTP calls (no code changes in business logic)
2. Detect unhealthy behavior (failure spikes, slow responses)
3. Inject resilience patterns automatically (retry, circuit breaker, timeout)
4. Remove patterns after stable recovery

Core flow:

Monitor -> Detector -> Injector <- Agent

## 2. Workflow At A Glance

Use this exact sequence for the demo workflow:

1. Start the fault proxy (injects faults on demand)
2. Start AutoHeal sidecar runner (installs monitor + starts autonomous agent + generates traffic)
3. Start the dashboard (observe health, events, and active patterns)
4. Inject controlled faults (via chaos_control)
5. Observe automated pattern injection and later removal after recovery

## 3. Prerequisites

From project root:

```bash
pip install flask requests
```

Optional but recommended:

1. Use a virtual environment
2. Ensure ports 5000, 8000, and 8001 are available

## 4. Run The Full Workflow

Open three terminals at project root.

### Terminal 1: Start Fault Proxy

```bash
python saleor_sandbox/fault_proxy.py
```

Expected signal:

1. Proxy prints it is running on port 8001

### Terminal 2: Start Sidecar + Agent + Traffic

```bash
python saleor_sandbox/runner.py
```

What this does:

1. Installs monitor by monkey-patching requests
2. Starts AutoHeal agent scan loop
3. Sends steady GraphQL traffic through proxy at localhost:8001

Expected signal:

1. Sidecar startup banner
2. Monitor installed message
3. Periodic agent scan output

### Terminal 3: Start Dashboard

```bash
python webapp/app.py
```

Open:

1. http://localhost:5000/
2. http://localhost:5000/dashboard

Expected signal:

1. Service cards appear after traffic starts
2. Stats update every few seconds
3. Event feed starts showing scan and action events

## 5. Inject Faults And Observe Healing

Open a fourth terminal at project root.

Service key used by proxy and monitor in this demo:

1. localhost:8000

### Scenario A: Transient failures (Retry expected)

```bash
python saleor_sandbox/chaos_control.py localhost:8000 status 503 0.4
```

Meaning:

1. Return HTTP 503 for about 40 percent of requests

Expected result:

1. Service becomes degraded
2. Agent may inject retry pattern
3. Event feed shows pattern injection details

### Scenario B: Critical failures (Circuit Breaker expected)

```bash
python saleor_sandbox/chaos_control.py localhost:8000 status 500 0.7
```

Meaning:

1. Return HTTP 500 for about 70 percent of requests

Expected result:

1. Service status can move to critical
2. Agent can inject circuit breaker
3. Dashboard highlights protected service and active pattern details

### Scenario C: Latency fault (Timeout possible)

```bash
python saleor_sandbox/chaos_control.py localhost:8000 delay 5 1.0
```

Meaning:

1. Add 5 second delay to all requests

Expected result:

1. Average latency rises
2. Detector may recommend timeout depending on observed metrics

## 6. Recovery Phase

Important: current proxy control updates fault config and does not provide full clear from CLI.

To return to clean state quickly:

1. Stop and restart Terminal 1 (fault_proxy.py)
2. Keep runner and dashboard running
3. Wait for grace period and healthy scans

Expected result:

1. Agent removes active pattern after stable health
2. Event feed shows pattern_removed event

## 7. What Happens Internally

### Monitoring

1. install_monitor() patches requests methods
2. Every call stores timestamp, duration, status, and error
3. Metrics are grouped by service host (for example localhost:8000)

### Detection

1. HealthDetector analyzes failure rate and average latency
2. State is classified as healthy, degraded, slow, critical, or unknown
3. Pattern decision tree selects best fit by failure signature

### Injection

1. PatternInjector records and manages active injections per service
2. Agent emits events for injections and removals
3. Patterns are removed when health remains stable for grace period

## 8. Dashboard API Mapping

The dashboard reads runtime state using these endpoints:

1. GET /api/services
2. GET /api/service/<service_name>
3. GET /api/stats
4. GET /api/agent/status
5. GET /api/agent/events
6. GET /api/injector/summary
7. POST /api/reset-demo
8. GET /api/patterns/info

## 9. Troubleshooting Quick Checks

### No services appear on dashboard

1. Confirm runner.py is running
2. Confirm monitor install message appears
3. Confirm traffic is being generated once per second

### Faults do not apply

1. Confirm fault proxy is running on port 8001
2. Confirm service key in command is localhost:8000
3. Check proxy terminal for injected error or delay logs

### No pattern injection happens

1. Increase fault rate or severity
2. Wait for several scan cycles
3. Verify there are enough recent calls for detector analysis

## 10. Where To Go Next

1. Deep pattern behavior: docs/patterns_deep_dive.md
2. Full API details: docs/API_REFERENCE.md
3. Architecture internals: docs/architecture.md
4. Dashboard details: webapp/README.md
