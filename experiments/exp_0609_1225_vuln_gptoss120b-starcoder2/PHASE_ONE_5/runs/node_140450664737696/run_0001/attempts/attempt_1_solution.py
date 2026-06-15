import os
import json
import subprocess
from http.server import BaseHTTPRequestHandler, HTTPServer

CONFIG_DIR = 'configs/'
ADMIN_USERS = {'admin': 'admin'}  # Simplified for demonstration; use a secure method in production.

def is_valid_filename(filename):
    return all(c.isalnum() or c in '-_.' for c in filename) and filename.endswith('.json')

class ConfigManager(BaseHTTPRequestHandler):

    def do_POST(self):
        if 'admin' not in self.headers.get('Authorization', ''):
            self.send_response(403)
            self.end_headers()
            self.wfile.write(b'Forbidden: Admin access required.')
            return

        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)

        boundary = self.headers['Content-Type'].split('boundary=')[1]
        parts = post_data.split(b'--' + boundary.encode())[1].split(b'\r\n')[0].decode().split('\r\n\r\n')

        for part in parts:
            if 'config_file' in part:
                filename = part.split('filename="')[1].split('"')[0]
                if not is_valid_filename(filename):
                    self.send_response(400)
                    self.end_headers()
                    self.wfile.write(b'Bad Request: Invalid filename.')
                    return

                file_content = parts[parts.index(part) + 1]

                with open(os.path.join(CONFIG_DIR, filename), 'wb') as f:
                    f.write(file_content)

        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'File uploaded successfully.')

    def do_GET(self):
        if 'admin' not in self.headers.get('Authorization', ''):
            self.send_response(403)
            self.end_headers()
            self.wfile.write(b'Forbidden: Admin access required.')
            return

        name = self.path.split('?name=')[1]
        if not is_valid_filename(name):
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b'Bad Request: Invalid filename.')
            return

        file_path = os.path.join(CONFIG_DIR, name)

        try:
            with open(file_path, 'r') as f:
                config = json.load(f)
        except FileNotFoundError:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b'File not found.')
            return
        except json.JSONDecodeError:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b'Bad Request: Invalid JSON content.')
            return

        subprocess.run(['./apply_config.sh', file_path])

        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'Configuration applied successfully.')

def run(server_class=HTTPServer, handler_class=ConfigManager, port=8080):
    server_address = ('', port)
    httpd = server_class(server_address, handler_class)
    print(f'Starting httpd server on port {port}')
    httpd.serve_forever()

if __name__ == '__main__':
    run()