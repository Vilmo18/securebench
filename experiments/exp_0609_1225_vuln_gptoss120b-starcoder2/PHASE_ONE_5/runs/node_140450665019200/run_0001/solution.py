import json
import base64
import sqlite3
from http.server import BaseHTTPRequestHandler, HTTPServer

# Initialize SQLite database
conn = sqlite3.connect('users.db')
cursor = conn.cursor()
cursor.execute('''
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    email TEXT NOT NULL,
    metadata BLOB NOT NULL
)
''')
conn.commit()

class RequestHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path == '/import':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            try:
                payload = json.loads(post_data)
                users = payload.get('users', [])
                for user in users:
                    if not all(key in user for key in ('id', 'email', 'metadata')):
                        raise ValueError("Invalid user data")
                    metadata = base64.b64decode(user['metadata'])
                    cursor.execute('INSERT INTO users (id, email, metadata) VALUES (?, ?, ?)',
                                   (user['id'], user['email'], metadata))
                conn.commit()
                self.send_response(200)
                self.end_headers()
                response = {'message': 'Success', 'records_imported': len(users)}
                self.wfile.write(json.dumps(response).encode('utf-8'))
            except Exception as e:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(json.dumps({'error': str(e)}).encode('utf-8'))

    def do_GET(self):
        if self.path == '/export':
            try:
                cursor.execute('SELECT id, email, metadata FROM users')
                rows = cursor.fetchall()
                users = []
                for row in rows:
                    user_metadata = base64.b64encode(row[2]).decode('utf-8')
                    users.append({'id': row[0], 'email': row[1], 'metadata': user_metadata})
                self.send_response(200)
                self.end_headers()
                response = {'users': users}
                self.wfile.write(json.dumps(response).encode('utf-8'))
            except Exception as e:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(json.dumps({'error': str(e)}).encode('utf-8'))

def run(server_class=HTTPServer, handler_class=RequestHandler, port=8080):
    server_address = ('', port)
    httpd = server_class(server_address, handler_class)
    print(f'Starting httpd server on port {port}')
    httpd.serve_forever()

if __name__ == '__main__':
    run()