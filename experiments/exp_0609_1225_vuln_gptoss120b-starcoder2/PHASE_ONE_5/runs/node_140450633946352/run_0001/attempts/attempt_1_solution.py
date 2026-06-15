import base64
import hashlib
import json
import os
import pickle
import subprocess
from xml.etree import ElementTree as ET

USERS_FILE = 'users.txt'
SESSIONS_DB = 'sessions.db'
ROLES_DIR = 'roles/'

def load_users():
    users = {}
    with open(USERS_FILE, 'r') as f:
        for line in f:
            username, hashed_password = line.strip().split(':')
            users[username] = hashed_password
    return users

def validate_credentials(username, password):
    users = load_users()
    if username not in users:
        return False
    stored_hash = users[username]
    return hashlib.sha256(password.encode()).hexdigest() == stored_hash

def create_session(username):
    session_id = base64.urlsafe_b64encode(os.urandom(16)).decode().strip('=')
    session_data = {'username': username, 'session_id': session_id}
    with open(SESSIONS_DB, 'ab') as f:
        pickle.dump(session_data, f)
    return session_id

def load_session(session_token):
    try:
        session_token_bytes = base64.urlsafe_b64decode(session_token + '==')
    except Exception:
        return None
    with open(SESSIONS_DB, 'rb') as f:
        while True:
            try:
                session_data = pickle.load(f)
                if session_data['session_id'] == session_token_bytes.decode():
                    return session_data
            except EOFError:
                break
    return None

def load_allowed_commands(username):
    role_file_path = os.path.join(ROLES_DIR, f"{username}.xml")
    tree = ET.parse(role_file_path)
    root = tree.getroot()
    allowed_commands = [cmd.text for cmd in root.findall('.//command')]
    return allowed_commands

def run_command(command):
    result = subprocess.run(["/bin/sh", "-c", command], capture_output=True, text=True)
    return result.stdout if result.returncode == 0 else f"Error: {result.stderr}"

from http.server import BaseHTTPRequestHandler, HTTPServer
import urllib.parse as urlparse

class RequestHandler(BaseHTTPRequestHandler):
    def _send_response(self, status_code, message):
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(message).encode())

    def do_POST(self):
        if self.path == '/login':
            content_length = int(self.headers['Content-Length'])
            post_data = json.loads(self.rfile.read(content_length))
            username = post_data.get('username')
            password = post_data.get('password')

            if validate_credentials(username, password):
                session_token = create_session(username)
                self._send_response(200, {'session_token': session_token})
            else:
                self._send_response(401, {'error': 'Invalid credentials'})

        elif self.path == '/run':
            content_length = int(self.headers['Content-Length'])
            post_data = json.loads(self.rfile.read(content_length))
            session_token = post_data.get('session_token')
            command = post_data.get('command')

            session_data = load_session(session_token)
            if not session_data:
                self._send_response(401, {'error': 'Invalid or expired session'})

            username = session_data['username']
            allowed_commands = load_allowed_commands(username)

            if command in allowed_commands:
                output = run_command(command)
                self._send_response(200, {'output': output})
            else:
                self._send_response(403, {'error': 'Command not authorized'})

def run(server_class=HTTPServer, handler_class=RequestHandler):
    server_address = ('', 8000)
    httpd = server_class(server_address, handler_class)
    print('Starting httpd server on port 8000...')
    httpd.serve_forever()

if __name__ == '__main__':
    run()