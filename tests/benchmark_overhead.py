import time
import requests
import statistics
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from autoheal.monitor import TelemetryMonitor, install_monitor, uninstall_monitor

def benchmark_requests(url, count=20):
    latencies = []
    for _ in range(count):
        start = time.time()
        try:
            requests.get(url, timeout=5)
        except:
            pass
        latencies.append(time.time() - start)
    return statistics.mean(latencies), statistics.stdev(latencies)

def run_benchmark():
    url = "https://www.google.com" # Using a reliable external URL
    
    print("=== AutoHeal-Py Performance Benchmark ===")
    
    # 1. Base Latency (No instrumentation)
    print("Measuring base requests latency...")
    base_mean, base_std = benchmark_requests(url)
    print(f"Base: {base_mean*1000:.2f}ms (std: {base_std*1000:.2f}ms)")
    
    # 2. Instrumented Latency
    print("\nInstalling AutoHeal Monitor...")
    monitor = TelemetryMonitor()
    install_monitor()
    
    print("Measuring instrumented requests latency...")
    inst_mean, inst_std = benchmark_requests(url)
    print(f"Inst: {inst_mean*1000:.2f}ms (std: {inst_std*1000:.2f}ms)")
    
    overhead = (inst_mean - base_mean) * 1000
    overhead_pct = (inst_mean / base_mean - 1) * 100
    
    print(f"\nResult:")
    print(f"Avg Overhead per call: {overhead:.3f}ms")
    print(f"Percentage increase: {overhead_pct:.2f}%")
    
    uninstall_monitor()
    print("==========================================")

if __name__ == "__main__":
    run_benchmark()
