"""
Verify that the Pattern 2 fix is working correctly
Run this AFTER restarting the webapp
"""
import urllib.request
import json
import time

def check_webapp_config():
    """Check if webapp is running with correct threshold"""
    print("=" * 70)
    print("VERIFICATION: Pattern 2 Fix")
    print("=" * 70)
    print()
    
    # Check if webapp is running
    try:
        resp = urllib.request.urlopen("http://localhost:5000/api/stats", timeout=2)
        print("✅ Webapp is running on port 5000")
    except Exception as e:
        print("❌ Webapp is NOT running!")
        print(f"   Error: {e}")
        print()
        print("   Please start the webapp:")
        print("   cd AutoHeal-Py")
        print("   python webapp/app.py")
        return False
    
    print()
    print("Checking detector configuration...")
    print("-" * 70)
    
    # The webapp creates a detector with the threshold
    # We can't directly query it, but we can check the code
    with open('webapp/app.py', 'r') as f:
        content = f.read()
        if 'critical_failure_threshold = 60.0' in content:
            print("✅ Code has correct threshold: 60.0%")
        elif 'critical_failure_threshold = 70.0' in content:
            print("❌ Code still has OLD threshold: 70.0%")
            print("   This should have been changed to 60.0%")
            return False
        else:
            print("⚠️  Could not find threshold in code")
            return False
    
    print()
    print("Expected behavior:")
    print("-" * 70)
    print("Pattern 1 (50% errors):")
    print("  • Status: DEGRADED")
    print("  • Pattern: RETRY (blue)")
    print()
    print("Pattern 2 (98% errors):")
    print("  • Status: CRITICAL")
    print("  • Pattern: CIRCUIT BREAKER (amber/orange)")
    print("  • Measured rate: ~60-70% (due to 15s window)")
    print()
    print("Pattern 3 (8s latency):")
    print("  • Status: SLOW")
    print("  • Pattern: TIMEOUT (purple)")
    print()
    
    print("=" * 70)
    print("✅ Configuration is correct!")
    print("=" * 70)
    print()
    print("Next steps:")
    print("1. Make sure webapp is restarted (Ctrl+C then python webapp/app.py)")
    print("2. Run: python saleor_sandbox/live_demo.py")
    print("3. Watch the dashboard at http://localhost:5000/dashboard")
    print()
    return True

if __name__ == "__main__":
    check_webapp_config()
