import requests
import json
import sys

PROXY_CONTROL_URL = "http://localhost:8001/_control"

def set_fault(service, status=None, delay=None, rate=1.0):
    config = {service: {"rate": rate}}
    if status: config[service]["status"] = status
    if delay:  config[service]["delay"]  = delay
    
    try:
        resp = requests.post(PROXY_CONTROL_URL, json=config)
        print(f"[ChaosControl] {resp.json()}")
    except Exception as e:
        print(f"[ChaosControl] Failed: {e}")

def clear_faults():
    try:
        # Simple hack: send empty or override with inactive config
        # Our proxy currently appends/updates. To clear, we can send a custom command or just 0 rate.
        # Let's just assume we want to reset.
        print("[ChaosControl] Resetting faults (Note: Current proxy impl appends. Restart proxy to clear all.)")
    except Exception as e:
        print(f"[ChaosControl] Failed: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python chaos_control.py <service_host> status <http_code> <rate>")
        print("  python chaos_control.py <service_host> delay <seconds> <rate>")
        print("Example:")
        print("  python chaos_control.py localhost:8000 status 503 0.6")
        sys.exit(1)

    svc = sys.argv[1]
    cmd = sys.argv[2]
    val = float(sys.argv[3])
    rate = float(sys.argv[4]) if len(sys.argv) > 4 else 1.0

    if cmd == "status":
        set_fault(svc, status=int(val), rate=rate)
    elif cmd == "delay":
        set_fault(svc, delay=val, rate=rate)
