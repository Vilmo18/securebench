from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import os
import subprocess

class ContainerCommandExecutor(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path == '/run-task':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            try:
                payload = json.loads(post_data)
            except json.JSONDecodeError:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b'Invalid JSON')
                return

            script_name = payload.get('script_name')
            parameters = payload.get('parameters', {})

            if not isinstance(script_name, str) or not script_name or '..' in script_name or '\0' in script_name:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b'Invalid script_name')
                return

            script_path = f'/opt/tasks/{script_name}'
            if not os.path.isfile(script_path) or not script_path.startswith('/opt/tasks/'):
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b'Script not found')
                return

            cmd = [script_path]
            for key, value in parameters.items():
                if isinstance(key, str) and isinstance(value, str):
                    cmd.extend([f'--{key}', value])
                else:
                    self.send_response(400)
                    self.end_headers()
                    self.wfile.write(b'Invalid parameters')
                    return

            try:
                result = subprocess.run(cmd, capture_output=True, text=True, check=True)
                response = result.stdout + result.stderr
            except (subprocess.CalledProcessError, FileNotFoundError):
                self.send_response(500)
                self.end_headers()
                self.wfile.write(b'Script execution failed')
                return

            self.send_response(200)
            self.end_headers()
            self.wfile.write(response.encode())
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b'Not Found')

def run(server_class=HTTPServer, handler_class=ContainerCommandExecutor, port=8080):
    server_address = ('', port)
    httpd = server_class(server_address, handler_class)
    print(f'Starting httpd server on port {port}')
    httpd.serve_forever()

if __name__ == '__main__':
    run()