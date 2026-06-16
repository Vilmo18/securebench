import json
import re
import sqlite3
from queue import Queue
from http.server import BaseHTTPRequestHandler, HTTPServer

# Initialize in-memory queue
message_queue = Queue()

# Predefined roles
VALID_ROLES = {'admin', 'user', 'guest'}

# Email regex pattern
EMAIL_PATTERN = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')

class ProfileSyncHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path != '/sync':
            self.send_error(404, 'Not Found')
            return

        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        
        try:
            data = json.loads(post_data)
        except json.JSONDecodeError:
            self.send_error(400, 'Invalid JSON')
            return

        user_id = data.get('user_id')
        new_email = data.get('new_email')
        role = data.get('role')

        if not isinstance(user_id, int) or not isinstance(new_email, str) or not isinstance(role, str):
            self.send_error(400, 'Invalid data types')
            return

        if not EMAIL_PATTERN.match(new_email):
            self.send_error(400, 'Invalid email format')
            return

        if role not in VALID_ROLES:
            self.send_error(400, f'Role must be one of {VALID_ROLES}')
            return

        conn = sqlite3.connect(':memory:')
        cursor = conn.cursor()
        cursor.execute('CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, email TEXT, role TEXT)')

        try:
            cursor.execute('UPDATE users SET email = ?, role = ? WHERE user_id = ?', (new_email, role, user_id))
            conn.commit()
            if cursor.rowcount == 0:
                self.send_error(400, 'User ID not found')
                return
        except sqlite3.Error as e:
            self.send_error(400, str(e))
            return
        finally:
            conn.close()

        message_queue.put(json.dumps({'user_id': user_id, 'action': 'updated'}))

        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({'status': 'success'}).encode())

def run(server_class=HTTPServer, handler_class=ProfileSyncHandler, port=8080):
    server_address = ('', port)
    httpd = server_class(server_address, handler_class)
    httpd.serve_forever()

if __name__ == '__main__':
    run()