import http.server
import urllib.parse
import http.cookies
import secrets

# In-memory user store
USERS = {"admin": "password123"}

# Session store
SESSIONS = {}

class RequestHandler(http.server.BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path == '/login':
            self.handle_login()
        else:
            self.send_error(404, "Not Found")

    def handle_login(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        params = urllib.parse.parse_qs(post_data.decode('utf-8'))

        username = params.get('username', [None])[0]
        password = params.get('password', [None])[0]
        csrf_token = params.get('csrf_token', [None])[0]

        if not self.validate_csrf_token(csrf_token):
            self.send_error(403, "CSRF Token Missing or Invalid")
            return

        if username in USERS and USERS[username] == password:
            session_id = secrets.token_urlsafe(16)
            SESSIONS[session_id] = username
            cookie = http.cookies.SimpleCookie()
            cookie['session_id'] = session_id
            cookie['session_id']['httponly'] = True
            self.send_response(302)
            self.send_header('Location', '/dashboard')
            self.send_header('Set-Cookie', cookie.output(header=''))
            self.end_headers()
        else:
            self.send_error(401, "Unauthorized")

    def do_GET(self):
        if self.path == '/dashboard':
            self.handle_dashboard()
        elif self.path == '/login':
            self.handle_login_form()
        else:
            self.send_error(404, "Not Found")

    def handle_dashboard(self):
        cookie = http.cookies.SimpleCookie(self.headers.get('Cookie', ''))
        session_id = cookie.get('session_id')
        if not session_id or session_id.value not in SESSIONS:
            self.send_error(401, "Unauthorized")
            return

        username = SESSIONS[session_id.value]
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(f"Welcome, {username}!".encode('utf-8'))

    def handle_login_form(self):
        csrf_token = secrets.token_urlsafe(16)
        form_html = f'''
            <form method="post" action="/login">
                Username: <input type="text" name="username"><br>
                Password: <input type="password" name="password"><br>
                CSRF Token: <input type="hidden" name="csrf_token" value="{csrf_token}"><br>
                <input type="submit" value="Login">
            </form>
        '''
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(form_html.encode('utf-8'))

    def validate_csrf_token(self, csrf_token):
        # In a real application, you would store the CSRF token in the user's session
        return True  # Simplified for this example

def run(server_class=http.server.HTTPServer, handler_class=RequestHandler, port=8000):
    server_address = ('', port)
    httpd = server_class(server_address, handler_class)
    print(f"Starting httpd server on port {port}")
    httpd.serve_forever()

if __name__ == '__main__':
    run()