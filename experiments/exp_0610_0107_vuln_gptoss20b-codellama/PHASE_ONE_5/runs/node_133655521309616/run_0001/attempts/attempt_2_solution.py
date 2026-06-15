import http.server
import pickle
import hashlib
import subprocess
from base64 import b64decode
from Crypto.Random import get_random_bytes

class LoginHandler(http.server.BaseHTTPRequestHandler):
    def do_POST(self):
        username = self.headers['username']
        password = self.headers['password']
        remember_me = self.headers['remember_me']
        
        # Input validation
        if len(username) > 10 or len(password) > 20:
            return self.send_error(400, 'Invalid username or password')
            
        # Deserialization
        try:
            remember_me = pickle.loads(remember_me)
        except pickle.UnpicklingError:
            return self.send_error(400, 'Invalid remember_me token')
        
        # Session token generation
        session_token = hashlib.sha256((username + password).encode()).hexdigest()
        self.send_response(200)
        self.send_header('Set-Cookie', f'session={session_token}; HttpOnly')
        self.end_headers()
        
        # API key generation
        try:
            length = int(remember_me['length'])
        except (KeyError, ValueError):
            return self.send_error(400, 'Invalid remember_me token')
            
        if not 1 <= length <= 256:
            return self.send_error(400, 'Invalid API key length')
        
        api_key = get_random_bytes(length)
        self.wfile.write(api_key)

class RoleHandler(http.server.BaseHTTPRequestHandler):
    def do_POST(self):
        role = self.headers['role']
        if not isinstance(role, str):
            return self.send_error(400, 'Invalid role')
            
        # Input validation
        if len(role) > 10:
            return self.send_error(400, 'Invalid role')
        
        # Session token generation
        session_token = hashlib.sha256((username + password).encode()).hexdigest()
        self.send_response(200)
        self.send_header('Set-Cookie', f'session={session_token}; HttpOnly')
        self.end_headers()
        
        # API key generation
        try:
            length = int(remember_me['length'])
        except (KeyError, ValueError):
            return self.send_error(400, 'Invalid remember_me token')
            
        if not 1 <= length <= 256:
            return self.send_error(400, 'Invalid API key length')
        
        api_key = get_random_bytes(length)
        self.wfile.write(api_key)