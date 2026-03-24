# AutoHeal-Py Teacher Project Brief

This document is designed for faculty review so the project can be understood quickly without reading all source code.

## 1. Project In One Line

AutoHeal-Py is a Python framework that automatically detects failing service calls at runtime and applies self-healing protection patterns without changing business code.

## 2. Problem Statement

Modern microservices fail in production because of:

1. Intermittent network errors
2. Service overload and 5xx bursts
3. Slow downstream dependencies

Without protection, one failing service can degrade the full system.

## 3. Proposed Solution

AutoHeal-Py introduces an autonomous control loop:

1. Observe: monitor all outgoing HTTP calls
2. Analyze: calculate failure rate and latency
3. Act: inject Retry, Circuit Breaker, or Timeout
4. Recover: remove protection after stable health

## 4. Core Innovation

1. Zero-touch instrumentation: runtime monkey patching of requests calls
2. Autonomous decisioning: pattern selection based on live failure signatures
3. Runtime adaptation: no redeploy required to apply or remove protection
4. Event-driven transparency: dashboard and event feed show all decisions

## 5. System Architecture (Simple View)

Traffic -> TelemetryMonitor -> HealthDetector -> AutoHealAgent -> PatternInjector -> Protected Calls

Module roles:

1. autoheal/monitor.py: captures request telemetry
2. autoheal/detector.py: evaluates health and recommends pattern
3. autoheal/agent.py: orchestrates periodic scan and decisions
4. autoheal/injector.py: manages active resilience pattern lifecycle
5. webapp/app.py: dashboard and API surface for visibility

## 6. Demo Workflow For Evaluation

Use 4 terminals.

### Terminal 1: Fault Proxy

```bash
python saleor_sandbox/fault_proxy.py
```

### Terminal 2: Sidecar Agent + Traffic

```bash
python saleor_sandbox/runner.py
```

### Terminal 3: Dashboard

```bash
python webapp/app.py
```

Open: http://localhost:5000/dashboard

### Terminal 4: Chaos Injection

Inject transient failures:

```bash
python saleor_sandbox/chaos_control.py localhost:8000 status 503 0.4
```

Inject critical failures:

```bash
python saleor_sandbox/chaos_control.py localhost:8000 status 500 0.7
```

Inject latency:

```bash
python saleor_sandbox/chaos_control.py localhost:8000 delay 5 1.0
```

Recovery reset:

1. Restart fault proxy process
2. Wait for grace period and healthy scans

## 7. What Teacher Should Observe

1. Dashboard service state transitions: healthy -> degraded/critical -> healthy
2. Event feed lines for pattern_injected and pattern_removed
3. Reduced visible request failures when Retry pattern is active
4. Fast-fail behavior under severe failure with Circuit Breaker

## 8. Measurable Outputs

1. Total calls monitored
2. Failure-rate trend under fault injection
3. Active pattern count over time
4. Recovery completion signal in event logs

## 9. Educational Value

This project demonstrates practical concepts in:

1. Microservice resilience engineering
2. Observability and telemetry design
3. Runtime adaptation and control loops
4. Fault injection testing and reliability validation

## 10. Suggested Viva Explanation (2 minutes)

AutoHeal-Py continuously monitors service-call health and automatically applies resilience patterns based on real-time metrics. The system does not require business-logic changes and adapts at runtime by injecting and removing patterns as service conditions change. During demo faults, the dashboard shows the closed-loop behavior from detection to recovery.

## 11. Relevant Documents

1. Full execution workflow: docs/WORKFLOW.md
2. Demo sequence: DEMO_GUIDE.md
3. Architecture detail: docs/architecture.md
4. Pattern internals: docs/patterns_deep_dive.md
5. API reference: docs/API_REFERENCE.md
