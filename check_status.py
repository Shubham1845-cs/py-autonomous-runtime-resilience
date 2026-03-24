import urllib.request
import json

r = urllib.request.urlopen('http://localhost:5000/api/services', timeout=5)
data = json.loads(r.read().decode())

if data:
    svc = data[0]
    print(f"Service: {svc['service']}")
    print(f"Status: {svc['status'].upper()}")
    print(f"Failure Rate: {svc['failure_rate']}%")
    print(f"Avg Latency: {svc['avg_latency']}s")
    print(f"Total Calls: {svc['total_calls']}")
    print(f"Active Pattern: {svc['active_pattern'] or 'None'}")
    if svc['pattern_details']:
        print(f"Pattern Config: {svc['pattern_details']['config']}")
else:
    print("No services found")
