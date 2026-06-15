import http.server
import sqlite3
import html
import urllib.parse
import os

DB_NAME = 'resources.db'
UPLOAD_DIR = 'uploads/'

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS resources (
                  id INTEGER PRIMARY KEY,
                  name TEXT,
                  path TEXT)''')
    conn.commit()
    conn.close()

class Handler(http.server.BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path == '/upload':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            params = urllib.parse.parse_qs(post_data.decode('utf-8'))
            filename = params.get('filename', [None])[0]
            file_content = params.get('file', [None])[0]

            if not filename or not file_content:
                self.send_response(400)
                self.end_headers()
                return

            if not self.validate_filename(filename):
                self.send_response(400)
                self.end_headers()
                return

            file_path = os.path.join(UPLOAD_DIR, filename)

            try:
                with open(file_path, 'wb') as f:
                    f.write(file_content.encode('utf-8'))

                conn = sqlite3.connect(DB_NAME)
                c = conn.cursor()
                c.execute("INSERT INTO resources (name, path) VALUES (?, ?)",
                          (filename, file_path))
                conn.commit()
                conn.close()

                self.send_response(201)
                self.end_headers()
            except Exception as e:
                self.send_response(500)
                self.end_headers()

    def do_GET(self):
        if self.path == '/catalog':
            try:
                conn = sqlite3.connect(DB_NAME)
                c = conn.cursor()
                c.execute("SELECT name, path FROM resources")
                rows = c.fetchall()
                conn.close()

                html_content = '<html><body>'
                for row in rows:
                    name, path = row
                    html_content += f'<a href="/files/{html.escape(name)}">{html.escape(name)}</a><br/>'
                html_content += '</body></html>'

                self.send_response(200)
                self.end_headers()
                self.wfile.write(html_content.encode('utf-8'))
            except Exception as e:
                self.send_response(500)
                self.end_headers()

    def validate_filename(self, filename):
        allowed_extensions = ['.png', '.jpg', '.pdf']
        if any(filename.endswith(ext) for ext in allowed_extensions):
            return True
        return False

if __name__ == '__main__':
    init_db()
    server = http.server.HTTPServer(('localhost', 8000), Handler)
    server.serve_forever()