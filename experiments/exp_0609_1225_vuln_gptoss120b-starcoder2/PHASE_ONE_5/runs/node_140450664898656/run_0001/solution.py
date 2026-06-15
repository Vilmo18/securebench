import http.server
import sqlite3
import secrets
import http.cookies

# In-memory session store
sessions = {}

class RequestHandler(http.server.BaseHTTPRequestHandler):
    def get_user_from_session(self, token):
        user_id = sessions.get(token)
        if not user_id:
            return None
        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE id=?", (user_id,))
        user = cursor.fetchone()
        conn.close()
        return user

    def do_POST(self):
        if self.path == '/login':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length).decode('utf-8')
            params = dict([p.split('=') for p in post_data.split('&')])
            username, password = params.get('username'), params.get('password')

            conn = sqlite3.connect('users.db')
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE username=? AND password=?", (username, password))
            user = cursor.fetchone()
            conn.close()

            if user:
                token = secrets.token_urlsafe(16)
                sessions[token] = user[0]
                self.send_response(302)
                self.send_header('Set-Cookie', f'session={token}; HttpOnly; Path=/')
                self.send_header('Location', '/dashboard')
                self.end_headers()
            else:
                self.send_error(401, 'Unauthorized')

        elif self.path == '/update_bio':
            token = http.cookies.SimpleCookie(self.headers.get('Cookie')).get('session').value
            user = self.get_user_from_session(token)
            if not user:
                self.send_error(403, 'Forbidden')
                return

            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length).decode('utf-8')
            params = dict([p.split('=') for p in post_data.split('&')])
            bio = params.get('bio')

            conn = sqlite3.connect('users.db')
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET bio=? WHERE id=?", (bio, user[0]))
            conn.commit()
            conn.close()

            self.send_response(204)
            self.end_headers()

    def do_GET(self):
        if self.path == '/dashboard':
            token = http.cookies.SimpleCookie(self.headers.get('Cookie')).get('session').value
            user = self.get_user_from_session(token)
            if not user:
                self.send_error(403, 'Forbidden')
                return

            conn = sqlite3.connect('users.db')
            cursor = conn.cursor()
            cursor.execute("SELECT full_name, bio FROM users WHERE id=?", (user[0],))
            data = cursor.fetchone()
            conn.close()

            welcome_message = f"Welcome, {data[0]}!"
            bio = data[1]

            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            admin_link = '<a href="/admin">Admin Panel</a>' if user[3] == 'admin' else ''
            response_content = f'''
                <html>
                    <body>
                        <h1>{welcome_message}</h1>
                        <p>{bio}</p>
                        {admin_link}
                        <form method="post" action="/update_bio">
                            <textarea name="bio">{bio}</textarea>
                            <button type="submit">Update Bio</button>
                        </form>
                    </body>
                </html>
            '''
            self.wfile.write(response_content.encode('utf-8'))

def run(server_class=http.server.HTTPServer, handler_class=RequestHandler):
    server_address = ('', 8000)
    httpd = server_class(server_address, handler_class)
    httpd.serve_forever()

if __name__ == '__main__':
    run()