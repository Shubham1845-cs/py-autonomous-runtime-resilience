# AutoHeal-Py: Professional Demo Guide

This guide walks you through a live demonstration of the AutoHeal-Py "Zero-Touch" self-healing capabilities using the Saleor E-commerce sandbox.

## 🏁 Prerequisites

Ensure you have the following processes running:
1.  **Fault Proxy**: `python saleor_sandbox/fault_proxy.py` (Port 8000)
2.  **AutoHeal Dashboard**: `python webapp/app.py` (Port 5000)

## 🎭 The Scenario

We are simulates a production environment where:
-   **Traffic** is flowing from customers to a **Saleor GraphQL API**.
-   The **AutoHeal Agent** is monitoring the traffic via the Fault Proxy.
-   **Chaos Control** allows us to inject faults into the system.

## 🎬 Act 1: Healthy Baseline
1.  **Start Traffic**: `python saleor_sandbox/runner.py`
2.  **Observe Dashboard**: Visit `http://localhost:5000`. You should see the service `saleor-api` appearing as **HEALTHY**.
3.  **Check Terminal**: The runner script shows successful 200 responses.

## 🎬 Act 2: Injecting Transient Failures (Retry)
1.  **Inject Chaos**: Run `python saleor_sandbox/chaos_control.py --status 503 --rate 0.4`
    -   *This injects a 40% failure rate (503 Service Unavailable).*
2.  **Watch the Agent**: Within 10-15 seconds, the Dashboard event feed will show:
    -   `[Agent] 🛡️ Injected 'retry' on 'saleor-api' | Reason: High failure rate (transient)`
3.  **The Result**: The `runner.py` terminal will show fewer errors because the Retry pattern is masking them!

## 🎬 Act 3: Injecting Critical Failures (Circuit Breaker)
1.  **Increase Chaos**: Run `python saleor_sandbox/chaos_control.py --status 500 --rate 0.7`
    -   *This injects a 70% failure rate (500 Internal Server Error).*
2.  **Watch the Agent**: The agent detects a **CRITICAL** state.
    -   `[Agent] 🛡️ Injected 'circuit_breaker' on 'saleor-api'`
3.  **The Result**: The Dashboard card for `saleor-api` will turn **RED**. Interaction stops to prevent system-wide collapse.

## 🎬 Act 4: Autonomous Recovery
1.  **Fix the Service**: Run `python saleor_sandbox/chaos_control.py --clear`
2.  **Wait for Grace Period**: In 30-60 seconds (scaled for demo), the agent will notice the service is healthy.
3.  **Observation**: 
    -   `[Agent] ✅ Removed 'circuit_breaker' from 'saleor-api' — service recovered.`
    -   The Dashboard card turns **GREEN** again.

## 📊 Act 5: Post-Mortem Report
Run `python saleor_sandbox/report.py` to see the statistical breakdown of how many failures were prevented by AutoHeal-Py.
