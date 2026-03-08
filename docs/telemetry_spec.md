# AutoHeal-Py: Telemetry Specification

This document defines the metrics data structure used by the `TelemetryMonitor` and the `HealthDetector`.

## 1. Call Metric Structure

Every intercepted HTTP call is stored as a JSON-serializable dictionary:

```json
{
  "timestamp": 1700000000.123,
  "duration": 0.450,
  "status": 200,
  "error": null
}
```

-   **timestamp**: Epoch time of the call completion.
-   **duration**: Total wall-clock time in seconds (float).
-   **status**: HTTP status code. `0` indicates a connection failure (before headers are received).
-   **error**: String representation of any raised exception (e.g., `"ConnectionRefusedError"`).

## 2. Analysis Windows

Telemetry is managed in a **Sliding Window**:
-   **Window Size**: Configurable (Default 60s).
-   **Storage**: Memory-efficient `collections.deque` with `maxlen`.
-   **Pruning**: Metrics older than the window are filtered out during health analysis to ensure the agent reacts only to *current* conditions.

## 3. Global Stats Calculation

### Failure Rate
Calculated as: `(Count of status >= 400 OR status == 0) / Total Calls * 100`.

### Latency
Calculated as: `Arithmetic Mean of duration` within the window.

## 4. API Export
The stats are exposed via the Dashboard API at `/api/stats`, enabling external monitoring tools (Prometheus, Grafana) to scrape AutoHeal-Py state.
