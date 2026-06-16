import http.server
import cgi
import html
import uuid
from urllib.parse import urlparse, parse_qs

class CommentApp(http.server.BaseHTTPRequestHandler):
    sessions = {}
    users_comments = {}

    def do_POST(self):
        if self.path == '/submit_comment':
            self.handle_submit_comment()
        elif self.path == '/delete_account':
            self.handle_delete_account()
        else:
            self.send_error(404, "Not Found")

    def handle_submit_comment(self):
        form = cgi.FieldStorage(
            fp=self.rfile,
            headers=self.headers,
            environ={'REQUEST_METHOD': 'POST', 'CONTENT_TYPE': self.headers['Content-Type']}
        )
        comment = form.getvalue('comment')
        csrf_token = form.getvalue('csrf_token')

        session_id = self.get_session_id()
        if not session_id or self.sessions[session_id] != csrf_token:
            self.render_error_page("Invalid CSRF Token")
            return

        if session_id not in self.users_comments:
            self.users_comments[session_id] = []
        self.users_comments[session_id].append(comment)
        self.render_success_page("Comment submitted successfully")

    def handle_delete_account(self):
        form = cgi.FieldStorage(
            fp=self.rfile,
            headers=self.headers,
            environ={'REQUEST_METHOD': 'POST', 'CONTENT_TYPE': self.headers['Content-Type']}
        )
        csrf_token = form.getvalue('csrf_token')

        session_id = self.get_session_id()
        if not session_id or self.sessions[session_id] != csrf_token:
            self.render_error_page("Invalid CSRF Token")
            return

        if session_id in self.users_comments:
            del self.users_comments[session_id]
        del self.sessions[session_id]
        self.send_response(302)
        self.send_header('Location', '/account_deleted')
        self.end_headers()

    def do_GET(self):
        if self.path == '/comments':
            self.render_comments_page()
        elif self.path == '/account_deleted':
            self.render_account_deleted_page()
        elif self.path == '/':
            self.render_home_page()
        else:
            self.send_error(404, "Not Found")

    def render_home_page(self):
        session_id = self.get_session_id()
        if not session_id:
            session_id = str(uuid.uuid4())
            self.sessions[session_id] = str(uuid.uuid4())

        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(b"<html><body>")
        self.wfile.write(b"<h1>Welcome to the Comment App</h1>")
        self.wfile.write(b"<form action='/submit_comment' method='post'>")
        self.wfile.write(b"Comment: <input type='text' name='comment'><br>")
        self.wfile.write(f"<input type='hidden' name='csrf_token' value='{self.sessions[session_id]}'>".encode())
        self.wfile.write(b"<input type='submit' value='Submit Comment'>")
        self.wfile.write(b"</form>")
        self.wfile.write(b"<form action='/delete_account' method='post'>")
        self.wfile.write(f"<input type='hidden' name='csrf_token' value='{self.sessions[session_id]}'>".encode())
        self.wfile.write(b"<input type='submit' value='Delete Account'>")
        self.wfile.write(b"</form>")
        self.wfile.write(b"</body></html>")

    def render_comments_page(self):
        session_id = self.get_session_id()
        if not session_id or session_id not in self.users_comments:
            self.send_error(403, "Forbidden")
            return

        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(b"<html><body>")
        self.wfile.write(b"<h1>Your Comments</h1>")
        self.wfile.write(b"<ul>")
        for comment in self.users_comments[session_id]:
            self.wfile.write(f"<li>{html.escape(comment)}</li>".encode())
        self.wfile.write(b"</ul>")
        self.wfile.write(b"<a href='/'>Back to Home</a>")
        self.wfile.write(b"</body></html>")

    def render_account_deleted_page(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(b"<html><body>")
        self.wfile.write(b"<h1>Account Deleted</h1>")
        self.wfile.write(b"<p>Your account has been successfully deleted.</p>")
        self.wfile.write(b"</body></html>")

    def render_success_page(self, message):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(b"<html><body>")
        self.wfile.write(f"<h1>{message}</h1>".encode())
        self.wfile.write(b"<a href='/'>Back to Home</a>")
        self.wfile.write(b"</body></html>")

    def render_error_page(self, message):
        self.send_response(400)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(b"<html><body>")
        self.wfile.write(f"<h1>Error: {message}</h1>".encode())
        self.wfile.write(b"<a href='/'>Back to Home</a>")
        self.wfile.write(b"</body></html>")

    def get_session_id(self):
        cookies = self.headers.get('Cookie')
        if not cookies:
            return None
        cookie_dict = dict(c.split('=') for c in cookies.split(';'))
        return cookie_dict.get('session_id')

    def send_headers(self, content_type='text/html'):
        self.send_response(200)
        self.send_header('Content-type', content_type)
        self.end_headers()

if __name__ == '__main__':
    server_address = ('', 8000)
    httpd = http.server.HTTPServer(server_address, CommentApp)
    httpd.serve_forever()