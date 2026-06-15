import os
import json
from http.server import BaseHTTPRequestHandler, HTTPServer

class FileProcessingService(BaseHTTPRequestHandler):
    ALLOWED_COMMANDS = {
        "compress": ["gzip", "-f"],
        "encrypt": ["openssl", "enc", "-aes-256-cbc", "-salt"]
    }
    UPLOADS_DIR = "uploads/"

    def _validate_command(self, command):
        return command in self.ALLOWED_COMMANDS

    def _validate_filename(self, filename):
        absolute_path = os.path.abspath(os.path.join(self.UPLOADS_DIR, filename))
        if not absolute_path.startswith(os.path.abspath(self.UPLOADS_DIR)):
            return False
        return True

    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        try:
            data = json.loads(post_data)
        except json.JSONDecodeError:
            self._send_error_response(400, "Invalid JSON payload")
            return

        command = data.get("command")
        filename = data.get("filename")

        if not command or not self._validate_command(command):
            self._send_error_response(400, "Invalid or disallowed command")
            return

        if not filename or not self._validate_filename(filename):
            self._send_error_response(400, "Invalid or disallowed filename")
            return

        absolute_path = os.path.abspath(os.path.join(self.UPLOADS_DIR, filename))
        cmd = self.ALLOWED_COMMANDS[command] + [absolute_path]

        try:
            import subprocess
            subprocess.run(cmd, check=True)
            self._send_success_response()
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            self._send_error_response(500, f"Command execution failed: {str(e)}")

    def _send_error_response(self, status_code, message):
        self.send_response(status_code)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        response = {"error": message}
        self.wfile.write(json.dumps(response).encode())

    def _send_success_response(self):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        response = {"status": "success"}
        self.wfile.write(json.dumps(response).encode())

def run(server_class=HTTPServer, handler_class=FileProcessingService, port=8080):
    server_address = ('', port)
    httpd = server_class(server_address, handler_class)
    print(f"Starting httpd server on port {port}")
    httpd.serve_forever()

if __name__ == "__main__":
    run()