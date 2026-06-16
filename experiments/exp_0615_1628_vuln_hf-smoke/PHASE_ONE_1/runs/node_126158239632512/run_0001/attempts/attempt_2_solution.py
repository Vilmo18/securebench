import os
import re
import html
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs
import base64

class EnvConfigServer(BaseHTTPRequestHandler):
    ADMIN_USER = os.getenv('ADMIN_USER', 'admin')
    ADMIN_PASS = os.getenv('ADMIN_PASS', 'adminpass')
    CSRF_TOKEN = os.getenv('CSRF_TOKEN', 'secure_csrf_token')

    def do_POST(self):
        if self.path == '/admin/set-env':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = parse_qs(post_data.decode('utf-8'))

            var_name = data.get('VAR_NAME', [''])[0]
            var_value = data.get('VAR_VALUE', [''])[0]
            csrf_token = data.get('CSRF_TOKEN', [''])[0]

            if not self.authenticate():
                self.send_response(401)
                self.end_headers()
                return

            if csrf_token != self.CSRF_TOKEN:
                self.send_response(403)
                self.end_headers()
                return

            if not self.validate_var_name(var_name):
                self.send_response(400)
                self.end_headers()
                return

            if not self.validate_var_value(var_value):
                self.send_response(400)
                self.end_headers()
                return

            os.environ[var_name] = var_value
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'Environment variable set successfully.')
        else:
            self.send_response(404)
            self.end_headers()

    def do_GET(self):
        if self.path.startswith('/status?'):
            query_components = parse_qs(self.path.split('?', 1)[1])
            var_name = query_components.get('var_name', [''])[0]
            var_value = os.getenv(var_name, 'Variable not set')
            escaped_var_value = html.escape(var_value)
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(f'<html><body><h1>{var_name}:</h1><p>{escaped_var_value}</p></body></html>'.encode('utf-8'))
        else:
            self.send_response(404)
            self.end_headers()

    def authenticate(self):
        auth = self.headers.get('Authorization')
        if not auth:
            return False
        try:
            username, password = base64.b64decode(auth.split()[1]).decode('utf-8').split(':')
            return username == self.ADMIN_USER and password == self.ADMIN_PASS
        except Exception:
            return False

    def validate_var_name(self, var_name):
        return re.match(r'^[A-Z0-9_]+$', var_name) is not None

    def validate_var_value(self, var_value):
        return re.match(r'^[\w\s\-\.\/]+$', var_value) is not None

def run(server_class=HTTPServer, handler_class=EnvConfigServer, port=8080):
    server_address = ('', port)
    httpd = server_class(server_address, handler_class)
    httpd.serve_forever()

if __name__ == '__main__':
    run()