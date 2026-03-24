"""
Quick restart script for AutoHeal-Py demo.
Kills old processes on ports 5000, 8000, 8001 and provides fresh start commands.
"""
import subprocess
import sys

def kill_port(port):
    """Kill process listening on a port (Windows)."""
    try:
        # Find PID
        result = subprocess.run(
            f'netstat -ano | findstr ":{port} " | findstr LISTENING',
            shell=True, capture_output=True, text=True
        )
        if result.stdout:
            lines = result.stdout.strip().split('\n')
            for line in lines:
                parts = line.split()
                if len(parts) >= 5:
                    pid = parts[-1]
                    print(f"[Kill] Port {port} → PID {pid}")
                    subprocess.run(f'taskkill /F /PID {pid}', shell=True, capture_output=True)
    except Exception as e:
        print(f"[Error] Could not kill port {port}: {e}")

if __name__ == "__main__":
    print("=" * 60)
    print("  AutoHeal-Py Demo Restart")
    print("=" * 60)
    
    print("\n[1] Killing old processes...")
    kill_port(5000)  # Dashboard
    kill_port(8001)  # Fault Proxy
    # Don't kill 8000 if it's a real Saleor instance
    
    print("\n[2] Ready to start fresh!")
    print("\nOpen 3 terminals and run:")
    print("\n  Terminal 1:")
    print("    python saleor_sandbox/fault_proxy.py")
    print("\n  Terminal 2:")
    print("    python saleor_sandbox/runner.py")
    print("\n  Terminal 3:")
    print("    python webapp/app.py")
    print("\nThen open: http://localhost:5000/dashboard")
    print("=" * 60)
