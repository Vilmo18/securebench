import http.server
import urllib.parse
import re
import random
import string

# Predefined administrator accounts
ADMIN_ACCOUNTS = {
    'admin_user': {'password': 'admin_pass', 'role': 'admin'},
}

# Fixed CSRF token for this exercise
CSRF_TOKEN = 'fixed_csrf_token'

# In-memory session map
SESSIONS = {}

def generate_session_id():
    return ''.join(random.choices(string.ascii_letters + string.digits, k=32))

class AdminLoginHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        parsed_path = urllib.parse.urlparse(self.path)
        query_params = urllib.parse.parse_qs(parsed_path.query)
        next_param = query_params.get('next', ['/admin/home'])[0]

        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()

        # HTML escape the next parameter
        escaped_next = next_param.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

        response_content = f"""
        <html>
            <body>
                <form method="post" action="/admin/login">
                    Username: <input type="text" name="username"><br>
                    Password: <input type="password" name="password"><br>
                    <input type="hidden" name="next" value="{escaped_next}">
                    <button type="submit">Login</button>
                </form>
                <span>Next: {escaped_next}</span>
            </body>
        </html>
        """
        self.wfile.write(response_content.encode('utf-8'))

    def do_POST(self):
        parsed_path = urllib.parse.urlparse(self.path)
        query_params = urllib.parse.parse_qs(parsed_path.query)
        next_param = query_params.get('next', ['/admin/home'])[0]

        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        post_params = urllib.parse.parse_qs(post_data.decode('utf-8'))

        username = post_params.get('username', [None])[0]
        password = post_params.get('password', [None])[0]

        # Validate username
        if not re.match(r'^[a-zA-Z0-9_]+$', username):
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b'Invalid username')
            return

        # Verify CSRF token
        csrf_token = self.headers.get('X-CSRF-Token')
        if csrf_token != CSRF_TOKEN:
            self.send_response(403)
            self.end_headers()
            self.wfile.write(b'CSRF token mismatch')
            return

        # Authenticate credentials and check role
        admin_account = ADMIN_ACCOUNTS.get(username)
        if not admin_account or admin_account['password'] != password or admin_account['role'] != 'admin':
            self.send_response(401)
            self.end_headers()
            self.wfile.write(b'Invalid username or password')
            return

        # Generate session ID and store it
        session_id = generate_session_id()
        SESSIONS[session_id] = {'username': username}

        # Set HTTP-Only cookie
        self.send_response(302)
        self.send_header('Set-Cookie', f'session={session_id}; HttpOnly; Path=/admin/')
        self.send_header('Location', next_param if next_param.startswith('/admin/') else '/admin/home')
        self.end_headers()

def run(server_class=http.server.HTTPServer, handler_class=AdminLoginHandler):
    server_address = ('', 8000)
    httpd = server_class(server_address, handler_class)
    print('Starting httpd server on port 8000...')
    httpd.serve_forever()

if __name__ == '__main__':
    run()