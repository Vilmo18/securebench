import os
import sqlite3
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs
from html import escape

DATABASE = 'notes.db'
NOTES_DIR = 'notes/'

def init_db():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS notes_index (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            filename TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

def sanitize_filename(title):
    return ''.join(c for c in title if c.isalnum() or c.isspace()).strip().replace(' ', '_')

class RequestHandler(BaseHTTPRequestHandler):

    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        params = parse_qs(post_data.decode('utf-8'))

        title = params.get('title', [''])[0].strip()
        body = params.get('body', [''])[0].strip()

        if not title or not body:
            self.send_response(400)
            self.end_headers()
            return

        sanitized_title = sanitize_filename(title)
        filename = os.path.join(NOTES_DIR, f"{sanitized_title}.txt")

        try:
            with open(filename, 'w') as file:
                file.write(body)

            conn = sqlite3.connect(DATABASE)
            cursor = conn.cursor()
            user_id = "user123"  # Example static user ID
            cursor.execute('INSERT INTO notes_index (user_id, filename) VALUES (?, ?)', (user_id, filename))
            conn.commit()
            conn.close()

            self.send_response(201)
        except Exception as e:
            self.send_response(500)

        self.end_headers()

    def do_GET(self):
        parsed_path = urlparse(self.path)
        query_params = parse_qs(parsed_path.query)

        keyword = query_params.get('keyword', [''])[0].strip()
        if not keyword:
            self.send_response(400)
            self.end_headers()
            return

        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()

        cursor.execute('SELECT filename FROM notes_index WHERE filename LIKE ?', ('%' + keyword + '%',))
        results = cursor.fetchall()
        conn.close()

        if not results:
            self.send_response(404)
            self.end_headers()
            return

        response_body = '<html><body><ul>'
        for row in results:
            filename = os.path.basename(row[0])
            title = escape(filename.replace('_', ' '))
            response_body += f'<li>{title}</li>'

        response_body += '</ul></body></html>'
        self.send_response(200)
        self.end_headers()
        self.wfile.write(response_body.encode('utf-8'))

if __name__ == '__main__':
    if not os.path.exists(NOTES_DIR):
        os.makedirs(NOTES_DIR)

    init_db()

    server_address = ('', 8000)
    httpd = HTTPServer(server_address, RequestHandler)
    print("Starting server on port 8000...")
    httpd.serve_forever()