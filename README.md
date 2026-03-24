
# AutoHeal-Py

AutoHeal-Py is a Python runtime self-healing framework that monitors outgoing HTTP calls, detects unhealthy service behavior, and autonomously applies resilience patterns.

## Start Here

Primary onboarding and workflow guide:

1. docs/WORKFLOW.md

## Project Flow

1. Install monitor (runtime instrumentation)
2. Start autonomous agent loop
3. Generate service traffic
4. Detect degraded or critical behavior
5. Inject retry, circuit breaker, or timeout pattern
6. Remove pattern after healthy recovery

## Quick Run

From project root, use separate terminals:

```bash
python saleor_sandbox/fault_proxy.py
python saleor_sandbox/runner.py
python webapp/app.py
```

Then inject faults with:

```bash
python saleor_sandbox/chaos_control.py localhost:8000 status 503 0.4
```

## Documentation

1. Workflow and commands: docs/WORKFLOW.md
2. Teacher presentation brief: docs/TEACHER_PROJECT_BRIEF.md
3. Quick reference: QUICK_START.md
4. Demo script walkthrough: DEMO_GUIDE.md
5. User guide: docs/USER_GUIDE.md
6. Architecture: docs/architecture.md
7. API details: docs/API_REFERENCE.md
8. Pattern internals: docs/patterns_deep_dive.md

