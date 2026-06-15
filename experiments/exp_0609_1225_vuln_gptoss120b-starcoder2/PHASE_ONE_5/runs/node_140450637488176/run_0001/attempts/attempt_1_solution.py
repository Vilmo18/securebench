import http.server
import sqlite3
import uuid
import os
import re
from urllib.parse import parse_qs

DB_NAME = 'users.db'
AVATARS_DIR = 'avatars/'

def validate_username(username):
    return bool(re.match(r'^[a-zA-Z0-9]{3,20}$', username))

def validate_avatar(file):
    if file['size'] > 2 * 1024 * 1024:
        return False
    if file['type'] not in ['image/png', 'image/jpeg']:
        return False
    return True

class UserProfileUpdateHandler(http.server.BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path != '/update_profile':
            self.send_error(404)
            return

        form = parse_qs(self.rfile.read(int(self.headers['Content-Length'])), keep_blank_values=True)

        csrf_token = form.get('csrf_token', [None])[0]
        username = form.get('username', [None])[0]
        avatar_file = form.get('avatar', [None])[0]

        if not csrf_token or csrf_token != self.client_address[0]:
            self.send_response(403)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(b'{"error": "Invalid CSRF token"}')
            return

        if not username or not validate_username(username):
            self.send_response(400)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(b'{"error": "Invalid username"}')
            return

        avatar_path = None
        if avatar_file:
            file_info = {
                'type': form.get('avatar_type', [None])[0],
                'size': int(form.get('avatar_size', [0])[0]),
                'filename': form.get('avatar_filename', [None])[0]
            }
            if not validate_avatar(file_info):
                self.send_response(400)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(b'{"error": "Invalid avatar"}')
                return

            safe_filename = re.sub(r'[^\w\.\-]', '_', file_info['filename'])
            ext = os.path.splitext(safe_filename)[1]
            unique_filename = str(uuid.uuid4()) + ext
            avatar_path = os.path.join(AVATARS_DIR, unique_filename)

        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        try:
            if avatar_path:
                cursor.execute("UPDATE users SET username=?, avatar_path=? WHERE session_id=?", (username, avatar_path, self.client_address[0]))
            else:
                cursor.execute("UPDATE users SET username=? WHERE session_id=?", (username, self.client_address[0]))
            conn.commit()
        except sqlite3.Error as e:
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(b'{"error": "Database error"}')
            return
        finally:
            conn.close()

        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(b'{"success": true}')

if __name__ == '__main__':
    os.makedirs(AVATARS_DIR, exist_ok=True)

    server = http.server.HTTPServer(('', 8000), UserProfileUpdateHandler)
    print("Server running on port 8000...")
    server.serve_forever()