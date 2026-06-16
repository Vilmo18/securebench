import os
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import unquote

LOGS_ROOT = "logs/"

def is_safe_path(basedir, path):
    path = os.path.normpath(unquote(path))
    return os.path.commonprefix([basedir, path]) == basedir

class ConfigUploadHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path != '/admin/upload_config':
            self.send_error(404, "Not Found")
            return

        # Check if the user has ADMIN role
        if self.headers.get('X-User-Role') != 'ADMIN':
            self.send_error(403, "Forbidden: User does not have ADMIN role")
            return

        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        boundary = self.headers.get_boundary()

        if not boundary:
            self.send_error(400, "Bad Request: Missing boundary")
            return

        parts = post_data.split(b"--" + boundary.encode())
        for part in parts:
            if b'form-data; name="config_file"' in part:
                lines = part.splitlines()
                for line in lines:
                    if line.startswith(b"Content-Type:"):
                        break
                else:
                    self.send_error(400, "Bad Request: Missing Content-Type")
                    return

                file_data = b"\r\n".join(lines[lines.index(b"") + 1:-2])
                try:
                    config = json.loads(file_data.decode('utf-8'))
                except (json.JSONDecodeError, UnicodeDecodeError) as e:
                    self.send_error(400, f"Bad Request: {str(e)}")
                    return

                if not isinstance(config, dict) or 'log_directory' not in config:
                    self.send_error(400, "Bad Request: Invalid configuration format")
                    return

                log_directory = config['log_directory']
                full_log_path = os.path.join(LOGS_ROOT, log_directory)

                if not is_safe_path(LOGS_ROOT, full_log_path):
                    self.send_error(403, "Forbidden: Unsafe log directory path")
                    return

                try:
                    os.makedirs(full_log_path, exist_ok=True, mode=0o750)
                except OSError as e:
                    self.send_error(500, f"Internal Server Error: {str(e)}")
                    return

                status_log_file = os.path.join(full_log_path, "config_update.log")
                try:
                    with open(status_log_file, "w") as f:
                        f.write("Configuration updated successfully.\n")
                except IOError as e:
                    self.send_error(500, f"Internal Server Error: {str(e)}")
                    return

                self.send_response(200)
                self.end_headers()
                return

        self.send_error(400, "Bad Request: No config_file found")

def run(server_class=HTTPServer, handler_class=ConfigUploadHandler, port=8080):
    server_address = ('', port)
    httpd = server_class(server_address, handler_class)
    httpd.serve_forever()

if __name__ == '__main__':
    run()