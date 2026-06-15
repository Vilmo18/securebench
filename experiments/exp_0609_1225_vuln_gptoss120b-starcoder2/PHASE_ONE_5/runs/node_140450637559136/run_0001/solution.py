import http.server
import os
import sqlite3
from pathlib import Path
import re

IMPORTS_DIR = Path('imports/')
IMPORTS_DIR.mkdir(exist_ok=True)
DB_PATH = 'imports.db'

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS imports_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_path TEXT NOT NULL,
            source_label TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

class ImportHandler(http.server.BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path != '/import':
            self.send_error(404, 'Not Found')
            return

        form = http.server.parse_form_data(self.rfile)
        file_item = form['data_file']
        source_label = form.getvalue('source_label', '')

        if not re.match(r'^[a-zA-Z0-9 _-]+$', source_label):
            self.send_response(400, 'Bad Request')
            self.end_headers()
            self.wfile.write(b'Invalid source label')
            return

        file_path = IMPORTS_DIR / Path(file_item.filename).name
        try:
            with open(file_path, 'wb') as f:
                f.write(file_item.file.read())

            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute('INSERT INTO imports_log (file_path, source_label) VALUES (?, ?)',
                           (str(file_path), source_label))
            conn.commit()
            conn.close()

            self.send_response(200, 'OK')
            self.end_headers()
            response = {'status': 'success', 'file': str(file_path.name)}
            self.wfile.write(bytes(json.dumps(response), 'utf-8'))

        except Exception as e:
            self.send_response(500, 'Internal Server Error')
            self.end_headers()
            self.wfile.write(str(e).encode())

if __name__ == '__main__':
    init_db()
    server = http.server.HTTPServer(('localhost', 8080), ImportHandler)
    print("Server running on port 8080...")
    server.serve_forever()