import hashlib
import hmac
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs
import xml.etree.ElementTree as ET
from defusedxml.ElementTree import fromstring

# In-memory user database
users_db = {
    "admin": hashlib.pbkdf2_hmac('sha256', "adminpass".encode(), b'salt', 100000).hex(),
    "user": hashlib.pbkdf2_hmac('sha256', "userpass".encode(), b'salt', 100000).hex()
}

# Secret key for signing tokens
SECRET_KEY = b'secret_key'

def generate_token(username, role):
    """Generate a signed session token."""
    token_data = f"{username}:{role}"
    signature = hmac.new(SECRET_KEY, token_data.encode(), hashlib.sha256).hexdigest()
    return f"{token_data}:{signature}"

def verify_token(token):
    """Verify the signed session token and extract user data."""
    try:
        token_data, signature = token.split(':')
        username, role = token_data.split(':')
        expected_signature = hmac.new(SECRET_KEY, token_data.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(signature, expected_signature):
            return None
        return username, role
    except (ValueError, TypeError):
        return None

def parse_profile_xml(xml_string):
    """Parse the XML to extract the <role> element value."""
    try:
        root = fromstring(xml_string)
        role_element = root.find('role')
        if role_element is not None:
            return role_element.text
    except ET.ParseError:
        pass
    return None

def validate_credentials(username, password):
    """Validate the username and password against the in-memory user database."""
    hashed_password = hashlib.pbkdf2_hmac('sha256', password.encode(), b'salt', 100000).hex()
    stored_password = users_db.get(username)
    if stored_password and hmac.compare_digest(stored_password, hashed_password):
        return True
    return False

def role_based_access_check(role):
    """Decorator to check the session token and ensure the user’s role permits access."""
    def decorator(func):
        def wrapper(handler, *args, **kwargs):
            token = handler.headers.get('Authorization')
            if not token:
                handler.send_response(401)
                handler.end_headers()
                handler.wfile.write(b"Unauthorized: Missing token")
                return
            user_data = verify_token(token)
            if not user_data or user_data[1] != role:
                handler.send_response(403)
                handler.end_headers()
                handler.wfile.write(b"Forbidden: Insufficient permissions")
                return
            return func(handler, *args, **kwargs)
        return wrapper
    return decorator

class RequestHandler(BaseHTTPRequestHandler):
    def _send_json_response(self, status_code, message):
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        response = json.dumps({"message": message})
        self.wfile.write(response.encode())

    def do_POST(self):
        if self.path == '/login':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            try:
                data = json.loads(post_data)
            except json.JSONDecodeError:
                self._send_json_response(400, "Invalid JSON")
                return

            username = data.get('username')
            password = data.get('password')
            profile_xml = data.get('profile_xml')

            if not isinstance(username, str) or not username:
                self._send_json_response(400, "Invalid username")
                return
            if not isinstance(password, str) or not password:
                self._send_json_response(400, "Invalid password")
                return

            if not validate_credentials(username, password):
                self._send_json_response(401, "Authentication failed")
                return

            role = 'admin'  # Default role
            if profile_xml:
                role = parse_profile_xml(profile_xml)
                if role is None:
                    self._send_json_response(400, "Invalid profile XML")
                    return

            token = generate_token(username, role)
            self._send_json_response(200, {"token": token})
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"Not Found")

    @role_based_access_check('admin')
    def do_GET(self):
        parsed_path = urlparse(self.path)
        if parsed_path.path.startswith('/admin/'):
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"Welcome, Admin!")
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"Not Found")

def run(server_class=HTTPServer, handler_class=RequestHandler, port=8080):
    server_address = ('', port)
    httpd = server_class(server_address, handler_class)
    print(f"Starting httpd server on port {port}")
    httpd.serve_forever()

if __name__ == '__main__':
    run()