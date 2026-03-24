"""
Quick script to restart just the webapp (after code changes).
Keeps fault proxy and runner running.
"""
import subprocess
import time

def kill_port(port):
    """Kill process on port (Windows)."""
    try:
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
        print(f"[Error] {e}")

if __name__ == "__main__":
    print("=" * 60)
    print("  Restarting Webapp Only")
    print("=" * 60)
    
    print("\n[1] Killing webapp on port 5000...")
    kill_port(5000)
    
    print("\n[2] Waiting 2 seconds...")
    time.sleep(2)
    
    print("\n[3] Ready to restart!")
    print("\nIn Terminal 3, run:")
    print("    python webapp/app.py")
    print("\nThen run the demo:")
    print("    python saleor_sandbox/live_demo.py")
    print("=" * 60)
