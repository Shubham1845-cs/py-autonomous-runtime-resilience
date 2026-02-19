# AutoHeal-Py Dashboard - Quick Start Guide

## 🚀 Running the Dashboard

### Step 1: Install Dependencies
```bash
cd d:\Projects\AutoHeal-Py
pip install flask
```

### Step 2: Start the Dashboard
```bash
cd webapp
python app.py
```

The dashboard will be available at: **http://localhost:5000**

---

## 📱 Pages Overview

### 1. **Home** (`/`)
- Hero section with project overview
- Key features showcase
- Live system stats preview

### 2. **Dashboard** (`/dashboard`)
- Real-time service health monitoring
- Global statistics (services, calls, patterns)
- Service health cards with failure rates and latency

### 3. **Monitor** (`/monitor`)
- Detailed telemetry for individual services
- Service selector with time range options
- Pattern recommendations
- Recent call history table

### 4. **Patterns** (`/patterns`)
- Circuit Breaker explanation
- Retry pattern details
- Timeout guard information
- Visual state diagrams

### 5. **Docs** (`/docs`)
- Quick start guide
- Installation instructions
- API reference
- Usage examples

### 6. **Settings** (`/settings`)
- Monitor configuration
- Detection thresholds
- Pattern parameters

---

## 🧪 Testing the Dashboard

### Option 1: With Existing Monitor Data
If you've already run the monitor and made some HTTP calls:
```bash
cd webapp
python app.py
```
Visit http://localhost:5000/dashboard to see your services!

### Option 2: Generate Test Data
Create a test script to generate some traffic:

```python
# test_traffic.py
from autoheal.monitor import install_monitor
import requests
import time

install_monitor()

# Make some test calls
for i in range(10):
    try:
        requests.get('https://httpbin.org/status/200')  # Success
        requests.get('https://httpbin.org/status/500')  # Failure
        time.sleep(1)
    except:
        pass

print("Test traffic generated! Check the dashboard.")
```

Run it:
```bash
python test_traffic.py
```

Then start the dashboard:
```bash
cd webapp
python app.py
```

---

## 🎨 Features

### Real-Time Updates
- Dashboard refreshes every 2 seconds
- Monitor page refreshes every 3 seconds
- Live health status indicators

### Professional Design
- Modern dark theme with glassmorphism
- Gradient accents and smooth animations
- Responsive layout for all screen sizes
- Premium color scheme

### Interactive Elements
- Service selector with time range filters
- Pattern recommendations based on health
- Detailed metrics tables
- Progress bars for health scores

---

## 🔌 API Endpoints

The dashboard uses these API endpoints:

- `GET /api/services` - List all monitored services
- `GET /api/service/<name>` - Get detailed metrics for a service
- `GET /api/stats` - Get global statistics
- `GET /api/patterns/info` - Get pattern information

---

## 📊 What You'll See

When services are being monitored, you'll see:

1. **Service Cards** with:
   - Service name
   - Health status (Healthy/Degraded/Critical)
   - Failure rate percentage
   - Average latency
   - Total call count
   - Health score progress bar

2. **Pattern Recommendations** when issues are detected:
   - Circuit Breaker for high failure rates
   - Retry for transient failures
   - Timeout for slow services

3. **Detailed Metrics** including:
   - Timestamp of each call
   - Duration
   - Status code
   - Error messages

---

## 🎯 Next Steps

1. **Start the dashboard**: `python webapp/app.py`
2. **Generate test traffic** (optional)
3. **Explore all pages** to see the full UI
4. **Integrate with your microservices** to see real monitoring

---

## 💡 Tips

- The dashboard works with the existing AutoHeal-Py backend
- No configuration needed - it automatically detects monitored services
- Use the Monitor page for detailed analysis
- Check the Patterns page to understand how each pattern works

Enjoy your professional AutoHeal-Py dashboard! 🎉
