import http.server
import urllib.parse
from html import escape

# In-memory storage
sessions = {}
users = {
    'user1': {'role': 'admin', 'display_name': 'Admin User'},
    'user2': {'role': 'user', 'display_name': 'Regular User'}
}

def get_user(session_id):
    user_id = sessions.get(session_id)
    return users.get(user_id)

def generate_csrf_token():
    import secrets
    return secrets.token_hex(16)

class ProfileHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        session_id = self.cookies.get('session_id')
        user = get_user(session_id)
        if not user:
            self.send_response(403)
            self.end_headers()
            return

        csrf_token = sessions[session_id]['csrf_token']
        display_name = escape(user['display_name'])
        admin_table = ''
        if user['role'] == 'admin':
            admin_table = '<table><tr><th>Username</th><th>Role</th></tr>'
            for username, info in users.items():
                admin_table += f'<tr><td>{escape(username)}</td><td>{escape(info["role"])}</td></tr>'
            admin_table += '</table>'

        response = f'''
        <html>
        <body>
            <h1>Welcome, {display_name}</h1>
            <form method="post">
                <input type="hidden" name="csrf_token" value="{csrf_token}">
                New Display Name: <input type="text" name="display_name">
                <input type="submit" value="Update">
            </form>
            {admin_table}
        </body>
        </html>
        '''

        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(response.encode())

    def do_POST(self):
        session_id = self.cookies.get('session_id')
        user = get_user(session_id)
        if not user:
            self.send_response(403)
            self.end_headers()
            return

        form_data = urllib.parse.parse_qs(self.rfile.read(int(self.headers['Content-Length'])).decode())
        csrf_token = form_data.get('csrf_token')[0]
        display_name = escape(form_data.get('display_name', [''])[0])

        if sessions[session_id]['csrf_token'] != csrf_token:
            self.send_response(403)
            self.end_headers()
            return

        user['display_name'] = display_name
        self.send_response(302)
        self.send_header('Location', '/profile')
        self.end_headers()

def run(server_class=http.server.HTTPServer, handler_class=ProfileHandler):
    server_address = ('', 8000)
    httpd = server_class(server_address, handler_class)
    httpd.serve_forever()

if __name__ == '__main__':
    import http.cookies
    ProfileHandler.cookies = http.cookies.SimpleCookie()
    run()