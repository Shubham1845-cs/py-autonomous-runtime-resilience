"""
Simple fault injection script that works with the fault proxy.
Usage: python inject_fault_simple.py <mode>
Modes: error_storm, latency_spike, partial_outage, clear
"""
import requests
import sys

PROXY_CONTROL = "http://localhost:8001/_control"

FAULTS = {
    "error_storm": {
        "localhost:8000": {"status": 503, "rate": 0.8}
    },
    "latency_spike": {
        "localhost:8000": {"delay": 6.0, "rate": 1.0}
    },
    "partial_outage": {
        "localhost:8000": {"status": 500, "rate": 0.5}
    },
    "clear": {
        "localhost:8000": {"rate": 0},
        "localhost:8001": {"rate": 0}
    }
}

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python inject_fault_simple.py <mode>")
        print("Modes:", ", ".join(FAULTS.keys()))
        sys.exit(1)
    
    mode = sys.argv[1]
    if mode not in FAULTS:
        print(f"Unknown mode: {mode}")
        print("Available:", ", ".join(FAULTS.keys()))
        sys.exit(1)
    
    config = FAULTS[mode]
    try:
        resp = requests.post(PROXY_CONTROL, json=config, timeout=5)
        print(f"✅ Injected: {mode}")
        print(f"Response: {resp.json()}")
    except Exception as e:
        print(f"❌ Failed: {e}")
