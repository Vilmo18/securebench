import os
import pathlib
import sqlite3
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs
from html import escape

ARTICLES_DIR = 'articles/'
DATABASE_FILE = 'articles.db'

def init_db():
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS articles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            filepath TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def sanitize_title(title):
    return ''.join(c if c.isalnum() or c == '-' else '' for c in title.lower())

class ArticleHandler(BaseHTTPRequestHandler):

    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        params = parse_qs(post_data.decode('utf-8'))

        title = params.get('title', [''])[0]
        body = params.get('body', [''])[0]

        if not title or not body:
            self.send_response(400)
            self.end_headers()
            return

        sanitized_title = sanitize_title(title)
        filename = f"{sanitized_title}.txt"
        filepath = os.path.join(ARTICLES_DIR, filename)

        # Ensure the path is safe
        if not os.path.commonprefix((os.path.abspath(filepath), ARTICLES_DIR)) == ARTICLES_DIR:
            self.send_response(400)
            self.end_headers()
            return

        # Write body to file
        with open(os.path.join(ARTICLES_DIR, filename), 'w', encoding='utf-8') as f:
            f.write(body)

        # Insert into database
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        cursor.execute('INSERT INTO articles (title, filepath) VALUES (?, ?)', (sanitized_title, filepath))
        conn.commit()
        conn.close()

        self.send_response(201)
        self.end_headers()

def run(server_class=HTTPServer, handler_class=ArticleHandler):
    os.makedirs(ARTICLES_DIR, exist_ok=True)
    init_db()
    server_address = ('', 8000)
    httpd = server_class(server_address, handler_class)
    print("Starting httpd server on port 8000...")
    httpd.serve_forever()

if __name__ == '__main__':
    run()