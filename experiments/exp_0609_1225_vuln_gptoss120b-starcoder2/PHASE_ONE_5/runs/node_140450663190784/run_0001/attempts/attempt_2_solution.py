import os
import json
import subprocess
from http.server import BaseHTTPRequestHandler, HTTPServer

class ConfigArchiveService(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path != '/upload':
            self.send_error(404)
            return

        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)

        boundary = self.headers['Content-Type'].split('boundary=')[1]
        parts = post_data.split(b'--' + boundary.encode())

        filename = None
        config_data = None

        for part in parts:
            if b'filename' in part:
                filename = part.split(b'\r\n\r\n')[1].decode().strip()
            elif b'config_data' in part:
                config_data = part.split(b'\r\n\r\n')[1].decode().strip()

        if not self.is_admin():
            self.send_response(403)
            self.end_headers()
            return

        try:
            json.loads(config_data)
        except json.JSONDecodeError:
            self.send_response(400)
            self.end_headers()
            return

        target_path = os.path.join('/var/app/configs', filename)

        if not self.is_safe_path(target_path):
            self.send_response(400)
            self.end_headers()
            return

        try:
            with open(target_path, 'w', encoding='utf-8') as f:
                f.write(config_data)
        except IOError:
            self.send_response(500)
            self.end_headers()
            return

        archive_path = os.path.join('/var/app/archives', filename + '.tar.gz')
        command = ['tar', '-czf', archive_path, '-C', '/var/app/configs', filename]
        try:
            subprocess.run(command, check=True)
        except subprocess.CalledProcessError as e:
            self.send_response(500)
            self.end_headers()
            return

        self.send_response(200)
        self.end_headers()

    def is_admin(self):
        # Placeholder for actual admin check
        return True

    def is_safe_path(self, path):
        base_dir = '/var/app/configs'
        real_base_dir = os.path.realpath(base_dir)
        real_path = os.path.realpath(path)

        if not real_path.startswith(real_base_dir + os.sep):
            return False
        return True

def run(server_class=HTTPServer, handler_class=ConfigArchiveService, port=8080):
    server_address = ('', port)
    httpd = server_class(server_address, handler_class)
    print(f'Starting httpd server on port {port}')
    httpd.serve_forever()

if __name__ == '__main__':
    run()