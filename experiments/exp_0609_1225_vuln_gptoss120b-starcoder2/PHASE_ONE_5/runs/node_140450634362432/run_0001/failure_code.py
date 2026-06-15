import json
import shlex
import subprocess
from http.server import BaseHTTPRequestHandler, HTTPServer

class TaskRunnerHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path != '/run-task':
            self.send_response(404)
            self.end_headers()
            return

        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)

        try:
            payload = json.loads(post_data)
        except json.JSONDecodeError:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b'Invalid JSON')
            return

        if 'command' not in payload or not isinstance(payload.get('command'), str):
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b'Missing or invalid command field')
            return

        env = payload.get('env', {})
        if not isinstance(env, dict):
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b'Invalid environment variables')
            return

        admin_role = 'admin'
        user_roles = self.headers.get('X-User-Roles', '')
        if admin_role not in user_roles.split(','):
            self.send_response(403)
            self.end_headers()
            self.wfile.write(b'Unauthorized access')
            return

        docker_cmd = ['docker', 'run', '--rm', '-i']
        for key, value in env.items():
            docker_cmd.extend(['-e', f'{key}={value}'])
        docker_cmd.append('myorg/task-runner:latest')
        docker_cmd.append(payload['command'])

        try:
            result = subprocess.run(docker_cmd, capture_output=True, text=True, check=True)
            self.send_response(200)
            self.end_headers()
            self.wfile.write(result.stdout.encode() + result.stderr.encode())
        except subprocess.CalledProcessError as e:
            self.send_response(500)
            self.end_headers()
            self.wfile.write(str(e).encode())
        except Exception as e:
            self.send_response(500)
            self.end_headers()
            self.wfile.write(str(e).encode())

def run(server_class=HTTPServer, handler_class=TaskRunnerHandler):
    server_address = ('', 8000)
    httpd = server_class(server_address, handler_class)
    print('Starting Task Runner HTTP Server...')
    httpd.serve_forever()

if __name__ == '__main__':
    run()