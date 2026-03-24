"""
Quick test to verify the detector threshold configuration
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from autoheal.monitor import TelemetryMonitor
from autoheal.detector import create_detector

# Create monitor and detector with the same config as webapp
monitor = TelemetryMonitor()
detector = create_detector(monitor,
    critical_failure_threshold = 60.0,
    degraded_failure_threshold = 10.0,
    slow_latency_threshold     = 3.0,
)

print("=" * 60)
print("Detector Configuration Test")
print("=" * 60)
print(f"Critical threshold: {detector.critical_threshold}%")
print(f"Degraded threshold: {detector.degraded_threshold}%")
print(f"Slow latency threshold: {detector.slow_threshold}s")
print()

# Simulate different failure rates
test_cases = [
    (30.0, "Should be DEGRADED → RETRY"),
    (50.0, "Should be DEGRADED → RETRY"),
    (59.9, "Should be DEGRADED → RETRY"),
    (60.0, "Should be CRITICAL → CIRCUIT BREAKER"),
    (70.0, "Should be CRITICAL → CIRCUIT BREAKER"),
    (98.0, "Should be CRITICAL → CIRCUIT BREAKER"),
]

print("Failure Rate Decision Tree:")
print("-" * 60)
for rate, expected in test_cases:
    from autoheal.detector import HealthState
    state = detector._determine_state(rate, 0.5)  # 0.5s latency (normal)
    print(f"{rate:5.1f}% → {state.value:10s} | {expected}")

print()
print("✅ If critical threshold is 60.0%, the test passed!")
print("   Pattern 2 (98% errors) should trigger CIRCUIT BREAKER")
