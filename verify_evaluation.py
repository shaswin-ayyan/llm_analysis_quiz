import http.server
import socketserver
import threading
import json
import os
import asyncio
from urllib.parse import urlparse, parse_qs
from app.config import settings

# Force enable AIPIPE
settings.USE_AIPIPE = True
# Ensure we use the right base URL
settings.AIPIPE_BASE_URL = "https://aipipe.org/openrouter/v1"

from app.orchestrator import Orchestrator

PORT = 8002
BASE_DIR = os.path.join(os.getcwd(), "tds-llm-analysis-main-tests", "public")

class MockServerHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=BASE_DIR, **kwargs)

    def do_POST(self):
        if self.path == "/submit":
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            try:
                data = json.loads(post_data)
                self.handle_submit(data)
            except Exception as e:
                self.send_error(400, str(e))
        else:
            self.send_error(404)

    def handle_submit(self, data):
        url = data.get("url")
        answer = data.get("answer")
        email = data.get("email")
        
        print(f"[SERVER] Received submission: URL={url}, Answer={answer}")
        
        response = {"correct": False, "reason": "Unknown task", "url": None}
        
        # Logic from worker.js (simplified)
        if "/demo" in url and "scrape" not in url and "audio" not in url:
            if answer:
                response = {
                    "correct": True, 
                    "reason": "", 
                    "url": f"http://localhost:{PORT}/demo-scrape.html?email={email}&id=1"
                }
            else:
                response = {"correct": False, "reason": "Empty answer"}
                
        elif "/demo-scrape" in url:
            # Expecting email number (mock logic)
            # In worker.js it calculates a number from email. 
            # For "alice@example.com", let's assume a fixed answer or check logic.
            # worker.js: emailNumber(email)
            # We'll accept any number for now to test connectivity, or try to match.
            # Let's just print it and say correct if it looks like a number.
            if str(answer).isdigit():
                 response = {
                    "correct": True, 
                    "reason": "", 
                    "url": f"http://localhost:{PORT}/demo-audio.html?email={email}&id=2"
                }
            else:
                 response = {"correct": False, "reason": "Expected a number"}

        elif "/demo-audio" in url:
             # Sum of numbers
             if str(answer).isdigit():
                 response = {
                    "correct": True, 
                    "reason": "", 
                    "url": None # End of chain
                }
        
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(response).encode())

def start_server():
    with socketserver.TCPServer(("", PORT), MockServerHandler) as httpd:
        print(f"Serving at port {PORT}")
        httpd.serve_forever()

async def run_orchestrator():
    await asyncio.sleep(2) # Wait for server to start
    
    orchestrator = Orchestrator()
    email = "alice@example.com"
    secret = "s3cret"
    start_url = f"http://localhost:{PORT}/demo.html"
    
    print(f"Starting Orchestrator with URL: {start_url}")
    
    # The orchestrator usually runs in background, but we want to await it if possible
    # or just fire it and wait for the server to receive requests.
    # Orchestrator.handle_task is async.
    
    try:
        await orchestrator.handle_task(start_url, email, secret)
        print("Orchestrator finished.")
    except Exception as e:
        print(f"Orchestrator failed: {e}")

if __name__ == "__main__":
    # Start server in a separate thread
    server_thread = threading.Thread(target=start_server, daemon=True)
    server_thread.start()
    
    # Run orchestrator
    asyncio.run(run_orchestrator())
