import http.server
import socketserver
import urllib.request
import threading
import json
import time
import random
from urllib.parse import urlparse

# --- Fault Configuration ---
# Example: {"payment-gateway": {"status": 500, "rate": 0.5}, "shipping-api": {"delay": 5.0, "rate": 1.0}}
faults = {}
faults_lock = threading.Lock()

class FaultProxyHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        self._handle_request()

    def do_POST(self):
        if self.path == "/_control":
            self._handle_control()
        else:
            self._handle_request()

    def do_PUT(self):
        self._handle_request()

    def do_DELETE(self):
        self._handle_request()

    def _handle_control(self):
        """Update fault configuration via POST /_control."""
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length)
            config = json.loads(body)
            
            with faults_lock:
                faults.update(config)
                
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok", "current_faults": faults}).encode())
        except Exception as e:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(str(e).encode())

    def _handle_request(self):
        """Proxy the request with optional fault injection."""
        # Extract target from header or path logic
        # For simplicity, we assume the proxy is reached and we proxy to a fixed target or based on 'Target-URL' header
        target_url = self.headers.get('X-Target-URL')
        if not target_url:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b"Missing X-Target-URL header")
            return

        parsed_target = urlparse(target_url)
        service_name = parsed_target.netloc

        # Check for faults
        applied_fault = None
        with faults_lock:
            if service_name in faults:
                fault_config = faults[service_name]
                if random.random() < fault_config.get("rate", 1.0):
                    applied_fault = fault_config

        if applied_fault:
            if "delay" in applied_fault:
                print(f"[FaultProxy] Injecting {applied_fault['delay']}s delay for {service_name}")
                time.sleep(applied_fault["delay"])
            
            if "status" in applied_fault and applied_fault["status"] > 0:
                print(f"[FaultProxy] Injecting Error {applied_fault['status']} for {service_name}")
                self.send_response(applied_fault["status"])
                self.end_headers()
                self.wfile.write(b"Injected Fault")
                return

        # Proxy the request
        try:
            req = urllib.request.Request(
                target_url,
                data=self.rfile.read(int(self.headers.get('Content-Length', 0))) if self.headers.get('Content-Length') else None,
                headers={k: v for k, v in self.headers.items() if k.lower() not in ['host', 'x-target-url']},
                method=self.command
            )
            
            with urllib.request.urlopen(req) as response:
                self.send_response(response.status)
                for k, v in response.getheaders():
                    self.send_header(k, v)
                self.end_headers()
                self.wfile.write(response.read())
        except Exception as e:
            print(f"[FaultProxy] Proxy Error: {e}")
            self.send_response(502)
            self.end_headers()
            self.wfile.write(str(e).encode())

def run_proxy(port=8001):
    with socketserver.ThreadingTCPServer(("", port), FaultProxyHandler) as httpd:
        print(f"[FaultProxy] Running on port {port}")
        httpd.serve_forever()

if __name__ == "__main__":
    run_proxy()
