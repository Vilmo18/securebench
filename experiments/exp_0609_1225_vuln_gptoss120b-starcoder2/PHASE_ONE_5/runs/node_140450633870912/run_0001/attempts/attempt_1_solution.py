from http.server import BaseHTTPRequestHandler, HTTPServer
import os
import subprocess
import html

SESSIONS = {}

class ContainerManager(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length).decode('utf-8')
        params = dict([p.split('=') for p in post_data.split('&')])

        container_name = params.get('container_name')
        label = html.escape(params.get('label', ''))
        csrf_token = params.get('csrf_token')

        if not self.validate_csrf(csrf_token):
            self.send_response(403)
            self.end_headers()
            return

        try:
            self.execute_docker_command(container_name)
            self.store_label(container_name, label)
            self.render_confirmation(label)
        except Exception as e:
            self.send_response(500)
            self.end_headers()
            self.wfile.write(str(e).encode('utf-8'))
            return

    def validate_csrf(self, csrf_token):
        session_id = self.headers.get('Cookie')
        if not session_id or SESSIONS.get(session_id) != csrf_token:
            return False
        return True

    def execute_docker_command(self, container_name):
        result = subprocess.run(['docker', 'start', container_name], capture_output=True)
        if result.returncode != 0:
            raise Exception(f"Failed to start container: {result.stderr.decode('utf-8')}")

    def store_label(self, container_name, label):
        metadata_dir = '/var/app/metadata/'
        os.makedirs(metadata_dir, exist_ok=True)
        with open(os.path.join(metadata_dir, f"{container_name}.txt"), 'w') as file:
            file.write(label)

    def render_confirmation(self, label):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(f"<html><body><p>{label}</p></body></html>".encode('utf-8'))

def run(server_class=HTTPServer, handler_class=ContainerManager, port=8080):
    server_address = ('', port)
    httpd = server_class(server_address, handler_class)
    print(f"Starting httpd server on port {port}")
    httpd.serve_forever()

if __name__ == "__main__":
    run()