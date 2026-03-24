import sys
import os
import time
import threading
import requests
import random

# Add parent directory to path to import autoheal
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from autoheal.monitor import TelemetryMonitor, install_monitor, _monitor
from autoheal.agent import create_agent

def start_sidecar():
    """
    Starts the AutoHeal sidecar.
    This effectively "inherits" the monitoring and healing logic for whatever 
    process runs it. In this demo, it monitors the load generator's calls 
    to Saleor.
    """
    print("====================================================")
    print("      AutoHeal-Py Saleor Sandbox Sidecar            ")
    print("====================================================")
    
    # 1. Install Monitor (Zero Code Change simulation)
    # This patches requests. In a real sidecar scenario, we'd wrap the 
    # target application or use environmental overrides.
    install_monitor()
    
    # 2. Start Autonomous Agent
    # We use a short scan interval for demo purposes
    agent = create_agent(_monitor, scan_interval=5)
    agent.start()
    
    print("[Sidecar] Monitor installed and Agent started.")
    print("[Sidecar] Monitoring all outgoing 'requests' calls...")

    # 3. Load Generation (integrated so it's monitored)
    print("[Sidecar] Starting simulated traffic to Saleor via Proxy...")
    
    PROXY_URL  = "http://localhost:8001/graphql/"
    TARGET_URL = "http://localhost:8000/graphql/"
    
    QUERIES = [
        "{ products(first: 5, channel: \"default-channel\") { edges { node { name } } } }",
        "{ categories(first: 5) { edges { node { name } } } }",
        "{ me { id email } }"
    ]

    try:
        while True:
            query = random.choice(QUERIES)
            try:
                # We call the PROXY and tell it where the REAL Saleor is
                # AutoHeal-Py tracks the call to the PROXY (localhost:8001)
                requests.post(
                    PROXY_URL, 
                    json={'query': query}, 
                    headers={"X-Target-URL": TARGET_URL},
                    timeout=30
                )
            except Exception as e:
                pass
            
            time.sleep(1.0) # 1 request per second
    except KeyboardInterrupt:
        print("[Sidecar] Stopping...")
        agent.stop()

if __name__ == "__main__":
    start_sidecar()
