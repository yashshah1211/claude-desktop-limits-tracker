"""
Claude.ai Limits Tracker - Local Web Server & API
Serves modern web dashboard and provides JSON API for desktop clients.
"""

import sys
import os
import json
import webbrowser
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse

# Reconfigure stdout for UTF-8
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

sys.path.insert(0, os.path.dirname(__file__))
from src.claude_client import get_status

PORT = 5173
WEB_DIR = os.path.join(os.path.dirname(__file__), "web")

class TrackerHTTPHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=WEB_DIR, **kwargs)

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/status":
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
            self.end_headers()
            data = get_status()
            self.wfile.write(json.dumps(data).encode("utf-8"))
            return
        
        # Fallback to serving web directory
        return super().do_GET()

    def log_message(self, format, *args):
        # Quiet logger for clean terminal
        pass

def run(open_browser=True):
    os.makedirs(WEB_DIR, exist_ok=True)
    server_address = ("127.0.0.1", PORT)
    httpd = HTTPServer(server_address, TrackerHTTPHandler)
    url = f"http://127.0.0.1:{PORT}"
    
    print("=" * 60)
    print(" ✦ Claude.ai Limits Tracker (Windows Web Dashboard)")
    print(f" -> Local Dashboard: {url}")
    print(f" -> Live Status API: {url}/api/status")
    print("=" * 60)
    print("Press Ctrl+C to stop the server.\n")

    if open_browser:
        webbrowser.open(url)

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping server...")
        httpd.server_close()

if __name__ == "__main__":
    open_b = "--no-browser" not in sys.argv
    run(open_browser=open_b)
