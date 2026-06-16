import os
import subprocess
from http.server import BaseHTTPRequestHandler, HTTPServer

class BuildTriggerHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if not self.path.startswith('/build'):
            self.send_error(404, 'Not Found')
            return

        query = self.path.split('?', 1)
        if len(query) != 2:
            self.send_error(400, 'Bad Request: Missing project parameter')
            return

        params = dict(q.split('=') for q in query[1].split('&'))
        project_name = params.get('project')
        if not project_name or not project_name.isalnum():
            self.send_error(400, 'Bad Request: Invalid project name')
            return

        base_dir = '/app/projects'
        project_path = os.path.join(base_dir, project_name)

        # Validate that the project path is within the base directory
        if not os.path.commonpath([base_dir, project_path]) == base_dir:
            self.send_error(400, 'Bad Request: Project directory not found')
            return

        dockerfile_path = os.path.join(project_path, 'Dockerfile')
        if not os.path.isfile(dockerfile_path):
            self.send_error(400, 'Bad Request: Dockerfile not found in project directory')
            return

        env_file_path = os.path.join(project_path, '.env')
        build_args = []
        if os.path.isfile(env_file_path):
            with open(env_file_path, 'r') as env_file:
                for line in env_file:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        key, value = line.split('=', 1)
                        build_args.append(f'--build-arg {key}={value}')

        build_command = ['docker', 'build'] + build_args + ['-t', f'{project_name}:latest', project_path]
        try:
            result = subprocess.run(build_command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(result.stdout)
        except subprocess.CalledProcessError as e:
            self.send_response(500)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(e.stderr)

def run(server_class=HTTPServer, handler_class=BuildTriggerHandler, port=8080):
    server_address = ('', port)
    httpd = server_class(server_address, handler_class)
    httpd.serve_forever()

if __name__ == '__main__':
    run()