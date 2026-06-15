import os
import subprocess
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs

# Simulated admin authentication (for demonstration purposes)
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = os.urandom(16).hex()

class AdminCommandDashboard(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/admin/command':
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            csrf_token = os.urandom(16).hex()
            self.server.csrf_tokens[self.client_address] = csrf_token
            response_content = f'''
                <html>
                    <body>
                        <form method="post" action="/admin/command">
                            <input type="hidden" name="csrf_token" value="{csrf_token}">
                            Command: <input type="text" name="cmd"><br>
                            <input type="submit" value="Execute">
                        </form>
                    </body>
                </html>
            '''
            self.wfile.write(response_content.encode('utf-8'))
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b'Not Found')

    def do_POST(self):
        if self.path == '/admin/command':
            form = parse_qs(self.rfile.read(int(self.headers['Content-Length'])).decode('utf-8'))
            cmd = form.get('cmd', [None])[0]
            csrf_token = form.get('csrf_token', [None])[0]

            if not self.server.csrf_tokens.get(self.client_address) == csrf_token:
                self.send_response(403)
                self.end_headers()
                self.wfile.write(b'CSRF token validation failed')
                return

            if cmd is None:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b'No command provided')
                return

            try:
                result = subprocess.run(cmd.split(), check=False, text=True, capture_output=True)
                exit_code = result.returncode
                output = result.stdout
            except Exception as e:
                exit_code = 1
                output = str(e)

            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            response_content = f'''
                <html>
                    <body>
                        Command "{cmd}" executed with exit code {exit_code}.<br>
                        Output: <pre>{output}</pre>
                    </body>
                </html>
            '''.encode('utf-8')
            self.wfile.write(response_content)
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b'Not Found')

def run(server_class=HTTPServer, handler_class=AdminCommandDashboard, port=8080):
    server = server_class(('localhost', port), handler_class)
    server.csrf_tokens = {}
    print(f'Starting server on port {port}')
    server.serve_forever()

if __name__ == '__main__':
    run()