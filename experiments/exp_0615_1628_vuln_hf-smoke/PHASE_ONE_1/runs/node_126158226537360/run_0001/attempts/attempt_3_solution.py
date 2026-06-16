import http.server
import socketserver
import os
import hashlib
import hmac
import secrets
from urllib.parse import urlparse, parse_qs
import html

# In-memory user store
users = {
    'alice': {'password': 'alicepass', 'files': ['alice_doc1.txt', 'alice_doc2.txt']},
    'bob': {'password': 'bobpass', 'files': ['bob_doc1.txt']}
}

# In-memory session store
sessions = {}

class SecureFileServer(http.server.SimpleHTTPRequestHandler):
    def do_POST(self):
        if self.path == '/login':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            username, password = post_data.decode().split('&')
            username = username.split('=')[1]
            password = password.split('=')[1]

            if self.verify_credentials(username, password):
                session_token = self.create_session(username)
                self.send_response(200)
                self.send_header('Set-Cookie', f'session={session_token}; HttpOnly; Secure')
                self.end_headers()
                self.wfile.write(b'Login successful')
            else:
                self.send_response(401)
                self.end_headers()
                self.wfile.write(b'Invalid credentials')
        else:
            self.send_response(405)
            self.end_headers()

    def do_GET(self):
        if self.path.startswith('/download'):
            session_token = self.get_session_token()
            if not session_token or not self.validate_session(session_token):
                self.send_response(403)
                self.end_headers()
                self.wfile.write(b'Forbidden')
                return

            username = sessions[session_token]['username']
            query_components = parse_qs(urlparse(self.path).query)
            file_name = query_components.get('file', [None])[0]

            if not file_name or not self.is_authorized(username, file_name):
                self.send_response(404)
                self.end_headers()
                self.wfile.write(b'File not found')
                return

            file_path = self.sanitize_file_path(file_name)
            if not file_path or not os.path.isfile(file_path):
                self.send_response(404)
                self.end_headers()
                self.wfile.write(b'File not found')
                return

            self.send_response(200)
            safe_filename = html.escape(os.path.basename(file_name))
            self.send_header('Content-Disposition', f'attachment; filename="{safe_filename}"')
            self.end_headers()
            with open(file_path, 'rb') as file:
                self.wfile.write(file.read())
        else:
            self.send_response(404)
            self.end_headers()

    def verify_credentials(self, username, password):
        user = users.get(username)
        return user and hmac.compare_digest(user['password'], password)

    def create_session(self, username):
        session_token = secrets.token_hex(16)
        sessions[session_token] = {'username': username}
        return session_token

    def get_session_token(self):
        cookie_header = self.headers.get('Cookie')
        if cookie_header:
            cookies = {cookie.split('=')[0]: cookie.split('=')[1] for cookie in cookie_header.split('; ')}
            return cookies.get('session')
        return None

    def validate_session(self, session_token):
        return session_token in sessions

    def is_authorized(self, username, file_name):
        user_files = users.get(username, {}).get('files', [])
        return file_name in user_files

    def sanitize_file_path(self, file_name):
        base_dir = 'private_docs'
        safe_path = os.path.join(base_dir, file_name)
        if os.path.commonpath([base_dir, safe_path]) != base_dir:
            return None
        return safe_path

PORT = 8000
with socketserver.TCPServer(("", PORT), SecureFileServer) as httpd:
    print("Serving at port", PORT)
    httpd.serve_forever()