# AutoHeal-Py Quick Start

Use this page for the fastest path. For full explanation, use docs/WORKFLOW.md.

## 1. Install Essentials

```bash
pip install flask requests
```

## 2. Start Core Processes

Run each command in a separate terminal from project root.

```bash
python saleor_sandbox/fault_proxy.py
```

```bash
python saleor_sandbox/runner.py
```

```bash
python webapp/app.py
```

Open:

1. http://localhost:5000/
2. http://localhost:5000/dashboard

## 3. Trigger Chaos

```bash
python saleor_sandbox/chaos_control.py localhost:8000 status 503 0.4
```

## 4. Observe Outcome

1. Service health changes on dashboard
2. Agent events appear for pattern injection
3. Patterns are removed after healthy recovery window

## 5. Canonical Guides

1. Full workflow: docs/WORKFLOW.md
2. Demo walkthrough: DEMO_GUIDE.md
3. API details: docs/API_REFERENCE.md
4. Architecture: docs/architecture.md
