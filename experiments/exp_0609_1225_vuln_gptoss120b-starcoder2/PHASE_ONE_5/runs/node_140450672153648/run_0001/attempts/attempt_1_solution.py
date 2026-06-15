import sqlite3
import hashlib
import hmac
import os
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from xml.etree.ElementTree import XMLParser

# Constants
DB_FILE = 'portal.db'
SESSION_EXPIRATION_SECONDS = 3600

class SafeXMLParser(XMLParser):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.set_feature(self.FEATURE_PROCESS_DTD, False)

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(stored_password: str, provided_password: str) -> bool:
    return hmac.compare_digest(stored_password, hash_password(provided_password))

def generate_session_token() -> str:
    return os.urandom(16).hex()

class XMLLoginHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path != '/api/xml_login':
            self.send_error(404)
            return

        content_length = int(self.headers['Content-Length'])
        raw_xml = self.rfile.read(content_length)

        try:
            parser = SafeXMLParser()
            parser.feed(raw_xml.decode())
            root = parser.close()

            username = root.find('Username').text
            password = root.find('Password').text

            if not (username and password and all(c.isprintable() for c in username + password)):
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b'{"error": "Invalid input"}')
                return

            conn = sqlite3.connect(DB_FILE)
            cursor = conn.cursor()

            cursor.execute("SELECT id, password_hash, role FROM users WHERE username = ?", (username,))
            user_record = cursor.fetchone()

            if not user_record or not verify_password(user_record[1], password):
                self.send_response(401)
                self.end_headers()
                self.wfile.write(b'{"error": "Authentication failed"}')
                return

            user_id, _, role = user_record
            session_token = generate_session_token()
            expires_at = int(time.time()) + SESSION_EXPIRATION_SECONDS

            cursor.execute("INSERT INTO sessions (user_id, token, expires_at) VALUES (?, ?, ?)",
                           (user_id, session_token, expires_at))
            conn.commit()

            self.send_response(200)
            self.end_headers()
            response = {
                'token': session_token,
                'role': role
            }
            self.wfile.write(bytes(json.dumps(response), "utf8"))

        except Exception as e:
            self.send_response(500)
            self.end_headers()
            self.wfile.write(b'{"error": "Internal server error"}')

    def do_GET(self):
        if not self.path.startswith('/admin/'):
            self.send_error(403)
            return

        token = self.headers.get('Authorization')
        if not token:
            self.send_error(401)
            return

        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()

        cursor.execute("SELECT user_id, expires_at FROM sessions WHERE token = ?", (token,))
        session_record = cursor.fetchone()

        if not session_record or int(time.time()) > session_record[1]:
            self.send_error(401)
            return

        user_id = session_record[0]
        cursor.execute("SELECT role FROM users WHERE id = ?", (user_id,))
        role_record = cursor.fetchone()

        if role_record and role_record[0] != 'admin':
            self.send_error(403)

if __name__ == '__main__':
    server_address = ('', 8000)
    httpd = HTTPServer(server_address, XMLLoginHandler)
    print("Starting server on port 8000...")
    httpd.serve_forever()