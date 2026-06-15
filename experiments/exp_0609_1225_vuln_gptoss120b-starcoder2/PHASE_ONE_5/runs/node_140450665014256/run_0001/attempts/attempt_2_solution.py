import sqlite3
import hashlib
import os
import hmac
from http.server import BaseHTTPRequestHandler, HTTPServer

# In-memory session store
sessions = {}

# Database setup
def init_db():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
                    username TEXT PRIMARY KEY,
                    password_hash TEXT,
                    role TEXT)''')
    # Add some test users
    admin_password = 'adminpass'
    user_password = 'userpass'

    def hash_password(password):
        return hashlib.pbkdf2_hmac('sha256', password.encode(), b'salt_1234567890', 100000).hex()

    c.execute("INSERT OR IGNORE INTO users (username, password_hash, role) VALUES ('admin', ?, 'admin')", [hash_password(admin_password)])
    c.execute("INSERT OR IGNORE INTO users (username, password_hash, role) VALUES ('user', ?, 'user')", [hash_password(user_password)])
    conn.commit()
    conn.close()

init_db()

class RequestHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path == '/login':
            self.handle_login()
        else:
            self.send_error(404, 'File not found')

    def handle_login(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        params = dict([p.split('=') for p in post_data.decode().split('&')])

        username = params.get('username')
        password = params.get('password')

        if not username or not password:
            self.send_error(400, 'Missing parameters')
            return

        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        c.execute("SELECT password_hash, role FROM users WHERE username=?", (username,))
        result = c.fetchone()
        conn.close()

        def verify_password(stored_password, provided_password):
            salt = b'salt_1234567890'
            pepper = b'pepper_1234567890'
            stored_hash = bytes.fromhex(stored_password)
            return hmac.compare_digest(
                hashlib.pbkdf2_hmac('sha256', provided_password.encode() + pepper, salt, 100000),
                stored_hash
            )

        if result and verify_password(result[0], password):
            session_id = os.urandom(16).hex()
            sessions[session_id] = {'username': username, 'role': result[1]}
            self.send_response(302)
            self.send_header('Location', f'/dashboard?session={session_id}')
            self.end_headers()
        else:
            self.send_error(401, 'Invalid credentials')

    def do_GET(self):
        if self.path.startswith('/dashboard'):
            self.handle_dashboard()
        elif self.path == '/login':
            self.show_login_form()
        else:
            self.send_error(404, 'File not found')

    def handle_dashboard(self):
        session_id = self.path.split('=')[-1]
        if session_id in sessions:
            user_info = sessions[session_id]
            html = f'''
            <html>
                <body>
                    <h1>Welcome, {user_info['username']}!</h1>
                    <ul>
                        <li><a href="#">Home</a></li>
                        {'<li><a href="#">Admin Panel</a></li>' if user_info['role'] == 'admin' else ''}
                    </ul>
                </body>
            </html>
            '''
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(html.encode())
        else:
            self.send_error(401, 'Unauthorized')

    def show_login_form(self):
        html = '''
        <html>
            <body>
                <form method="post" action="/login">
                    Username: <input type="text" name="username"><br>
                    Password: <input type="password" name="password"><br>
                    <input type="submit" value="Login">
                </form>
            </body>
        </html>
        '''
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(html.encode())

def run(server_class=HTTPServer, handler_class=RequestHandler, port=8080):
    server_address = ('', port)
    httpd = server_class(server_address, handler_class)
    print(f'Starting httpd server on port {port}')
    httpd.serve_forever()

if __name__ == '__main__':
    run()