import os
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs
import subprocess

# Mock session storage for CSRF token (in real scenario, this would be tied to user sessions)
SESSIONS = {
    "user1": {"csrf_token": "valid_csrf_token"}
}

ALLOWED_CONTAINERS = set(os.getenv("ALLOWED_CONTAINERS", "").split(","))

class ContainerManagerRequestHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path != "/containers/restart":
            self.send_error(404, "Endpoint not found")
            return

        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length)
        try:
            request_body = json.loads(post_data.decode("utf-8"))
        except json.JSONDecodeError:
            self.send_error(400, "Invalid JSON")
            return

        container_name = request_body.get('container_name')
        if not container_name or not isinstance(container_name, str):
            self.send_error(400, "Missing or invalid 'container_name' in request body")

        csrf_token = self.headers.get("X-CSRF-Token", "")
        user_session_key = self.headers.get("User-Session-Key", "")

        session_data = SESSIONS.get(user_session_key)
        if not session_data or session_data["csrf_token"] != csrf_token:
            self.send_error(403, "Invalid CSRF token")

        if container_name not in ALLOWED_CONTAINERS:
            self.send_error(403, "Container not permitted")
            return

        try:
            subprocess.run(["/usr/bin/docker", "restart", container_name], check=True)
            response = {"status": "success"}
        except subprocess.CalledProcessError as e:
            response = {"error": f"Restart failed: {str(e)}"}

        self.send_response(200 if "status" in response else 400)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(response).encode('utf-8'))

def run(server_class=HTTPServer, handler_class=ContainerManagerRequestHandler, port=8080):
    server_address = ('', port)
    httpd = server_class(server_address, handler_class)
    print(f"Starting httpd server on port {port}")
    httpd.serve_forever()

if __name__ == "__main__":
    run()