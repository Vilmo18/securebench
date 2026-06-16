import os
import http.server
import socketserver
from urllib.parse import urlparse, parse_qs
from http.cookies import SimpleCookie
from hashlib import sha256

class SecureLogServer(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        self.sessions = {}
        self.users = {
            'admin_user': {'password': sha256('admin_password'.encode()).hexdigest(), 'role': 'admin'},
            'regular_user': {'password': sha256('regular_password'.encode()).hexdigest(), 'role': 'user'}
        }
        super().__init__(*args, **kwargs)

    def do_POST(self):
        if self.path == '/login':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            username, password = self.parse_login_data(post_data)
            if self.authenticate(username, password):
                session_id = self.create_session(username)
                self.send_response(200)
                self.send_header('Set-Cookie', f'session_id={session_id}')
                self.end_headers()
                self.wfile.write(b'Login successful')
            else:
                self.send_response(403)
                self.end_headers()
                self.wfile.write(b'Forbidden')
        else:
            self.send_response(404)
            self.end_headers()

    def do_GET(self):
        if self.path.startswith('/download_log'):
            session_id = self.get_session_id()
            if session_id and self.sessions[session_id] == 'admin':
                query_components = parse_qs(urlparse(self.path).query)
                filename = query_components.get('filename', [None])[0]
                if filename:
                    self.serve_log_file(filename)
                else:
                    self.send_response(400)
                    self.end_headers()
            else:
                self.send_response(403)
                self.end_headers()
        else:
            self.send_response(404)
            self.end_headers()

    def parse_login_data(self, post_data):
        try:
            data = post_data.decode('utf-8')
            username = data.split('&')[0].split('=')[1]
            password = data.split('&')[1].split('=')[1]
            return username, password
        except Exception:
            return None, None

    def authenticate(self, username, password):
        if username in self.users and self.users[username]['password'] == sha256(password.encode()).hexdigest():
            return True
        return False

    def create_session(self, username):
        import uuid
        session_id = str(uuid.uuid4())
        self.sessions[session_id] = self.users[username]['role']
        return session_id

    def get_session_id(self):
        cookie = SimpleCookie(self.headers.get('Cookie'))
        return cookie.get('session_id', None) and cookie['session_id'].value

    def serve_log_file(self, filename):
        base_dir = '/var/app/logs/'
        full_path = os.path.join(base_dir, os.path.basename(filename))
        if os.path.isfile(full_path) and full_path.startswith(base_dir):
            with open(full_path, 'rb') as file:
                content = file.read()
            self.send_response(200)
            self.send_header('Content-Type', 'application/octet-stream')
            self.send_header('Content-Disposition', f'attachment; filename="{os.path.basename(filename)}"')
            self.end_headers()
            self.wfile.write(content)
        else:
            self.send_response(404)
            self.end_headers()

PORT = 8000
with socketserver.TCPServer(("", PORT), SecureLogServer) as httpd:
    print("Serving at port", PORT)
    httpd.serve_forever()