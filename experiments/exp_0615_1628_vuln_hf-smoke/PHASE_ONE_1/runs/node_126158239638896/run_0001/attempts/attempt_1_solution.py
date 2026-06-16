import http.server
import sqlite3
import http.cookies
import secrets
import time
import html
import re

class UserProfileService(http.server.BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path == '/login':
            self.handle_login()
        elif self.path == '/settings/update_email':
            self.handle_update_email()
        else:
            self.send_error(404, "Not Found")

    def do_GET(self):
        if self.path == '/profile':
            self.handle_profile()
        else:
            self.send_error(404, "Not Found")

    def handle_login(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length).decode('utf-8')
        username = post_data.split('&')[0].split('=')[1]
        password = post_data.split('&')[1].split('=')[1]

        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()
        cursor.execute("SELECT id, password_hash FROM users WHERE username=?", (username,))
        user = cursor.fetchone()
        conn.close()

        if user and self.verify_password(password, user[1]):
            session_id = secrets.token_hex(16)
            expires_at = int(time.time()) + 3600  # 1 hour session
            conn = sqlite3.connect('users.db')
            cursor = conn.cursor()
            cursor.execute("INSERT INTO sessions (session_id, user_id, expires_at) VALUES (?, ?, ?)", (session_id, user[0], expires_at))
            conn.commit()
            conn.close()

            cookie = http.cookies.SimpleCookie()
            cookie['SESSIONID'] = session_id
            cookie['SESSIONID']['httponly'] = True
            self.send_response(200)
            self.send_header('Set-Cookie', cookie.output(header='', sep=''))
            self.end_headers()
            self.wfile.write(b"<html><body><h1>Login Successful</h1></body></html>")
        else:
            self.send_response(401)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(b"<html><body><h1>Unauthorized</h1><p>Invalid username or password.</p></body></html>")

    def handle_profile(self):
        session_id = self.get_session_id()
        if not session_id:
            self.send_forbidden("Session ID missing.")
            return

        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()
        cursor.execute("SELECT user_id, expires_at FROM sessions WHERE session_id=?", (session_id,))
        session = cursor.fetchone()
        conn.close()

        if not session or session[1] < int(time.time()):
            self.send_forbidden("Session is invalid or expired.")
            return

        user_id = session[0]
        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()
        cursor.execute("SELECT full_name, bio, email FROM users WHERE id=?", (user_id,))
        user = cursor.fetchone()
        conn.close()

        if not user:
            self.send_error(404, "Not Found")
            return

        full_name, bio, email = user
        csrf_token = secrets.token_hex(16)

        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()
        cursor.execute("UPDATE sessions SET csrf_token=? WHERE session_id=?", (csrf_token, session_id))
        conn.commit()
        conn.close()

        escaped_bio = html.escape(bio)
        response_content = f"<html><body><h1>{full_name}</h1><p>{escaped_bio}</p><form action='/settings/update_email' method='post'><input type='hidden' name='csrf_token' value='{csrf_token}'><label for='new_email'>New Email:</label><input type='email' id='new_email' name='new_email'><button type='submit'>Update Email</button></form></body></html>"
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(response_content.encode('utf-8'))

    def handle_update_email(self):
        session_id = self.get_session_id()
        if not session_id:
            self.send_forbidden("Session ID missing.")
            return

        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()
        cursor.execute("SELECT user_id, expires_at, csrf_token FROM sessions WHERE session_id=?", (session_id,))
        session = cursor.fetchone()
        conn.close()

        if not session or session[1] < int(time.time()):
            self.send_forbidden("Session is invalid or expired.")
            return

        user_id, _, expected_csrf_token = session

        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length).decode('utf-8')
        new_email = post_data.split('&')[0].split('=')[1]
        csrf_token = post_data.split('&')[1].split('=')[1]

        if csrf_token != expected_csrf_token:
            self.send_forbidden("CSRF token mismatch.")
            return

        if not self.is_valid_email(new_email):
            self.send_error(400, "Bad Request")
            self.wfile.write(b"<html><body><h1>Bad Request</h1><p>Invalid email format.</p></body></html>")
            return

        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET email=? WHERE id=?", (new_email, user_id))
        conn.commit()
        conn.close()

        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(b"<html><body><h1>Email Updated Successfully</h1></body></html>")

    def get_session_id(self):
        cookie = http.cookies.SimpleCookie(self.headers.get('Cookie'))
        return cookie.get('SESSIONID', None) and cookie['SESSIONID'].value

    def verify_password(self, password, password_hash):
        # Placeholder for actual password verification logic (e.g., bcrypt)
        return password == password_hash

    def is_valid_email(self, email):
        return re.match(r"[^@]+@[^@]+\.[^@]+", email)

    def send_forbidden(self, message):
        self.send_response(403)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(f"<html><body><h1>Forbidden</h1><p>{message}</p></body></html>".encode('utf-8'))

def run(server_class=http.server.HTTPServer, handler_class=UserProfileService, port=8080):
    server_address = ('', port)
    httpd = server_class(server_address, handler_class)
    print(f'Starting httpd on port {port}...')
    httpd.serve_forever()

if __name__ == '__main__':
    run()