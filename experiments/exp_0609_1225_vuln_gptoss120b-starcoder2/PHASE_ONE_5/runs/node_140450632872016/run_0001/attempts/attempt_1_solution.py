import os
import sqlite3
import uuid
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs
import xml.etree.ElementTree as ET

# Constants
CONFIG_DIR = 'configs'
HELPER_DIR = 'helpers'
DB_FILE = 'admin_config.db'
CSRF_TOKEN_KEY = 'csrf_token'

# Ensure directories exist
os.makedirs(CONFIG_DIR, exist_ok=True)
os.makedirs(HELPER_DIR, exist_ok=True)

# Initialize SQLite database
conn = sqlite3.connect(DB_FILE)
cursor = conn.cursor()
cursor.execute('''
    CREATE TABLE IF NOT EXISTS settings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        db_table TEXT NOT NULL,
        record_id TEXT NOT NULL,
        value TEXT NOT NULL
    )
''')
conn.commit()

# Helper function to sanitize filenames
def safe_filename(filename):
    return uuid.uuid4().hex + os.path.splitext(filename)[1]

# Template for the helper script
HELPER_TEMPLATE = '''def apply_setting():
    print("{value}")
'''

class AdminConfigHandler(BaseHTTPRequestHandler):

    def do_POST(self):
        if self.path == '/admin/upload_config':
            form = parse_qs(self.rfile.read(int(self.headers['Content-Length'])))
            csrf_token = form.get('csrf_token', [None])[0]
            config_file = form.get('config_file', [None])[0]

            # Validate CSRF token
            if not self._validate_csrf_token(csrf_token):
                self.send_response(403)
                self.end_headers()
                self.wfile.write(b'{"error": "Invalid CSRF token"}')
                return

            # Process the uploaded file
            try:
                filename = safe_filename(config_file.filename)
                file_path = os.path.join(CONFIG_DIR, filename)

                with open(file_path, 'wb') as f:
                    f.write(config_file.file.read())

                # Parse XML securely
                tree = ET.parse(file_path)
                root = tree.getroot()

                db_table = root.find('db_table').text
                record_id = root.find('record_id').text
                value = root.find('value').text

                # Insert into SQLite database
                cursor.execute('''
                    INSERT INTO settings (db_table, record_id, value)
                    VALUES (?, ?, ?)
                ''', (db_table, record_id, value))
                conn.commit()

                # Generate helper script
                helper_filename = os.path.join(HELPER_DIR, f"{os.path.splitext(filename)[0]}_helper.py")
                with open(helper_filename, 'w') as f:
                    f.write(HELPER_TEMPLATE.format(value=value))

                self.send_response(200)
                self.end_headers()
                self.wfile.write(b'{"success": true}')

            except Exception as e:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(f'{{"error": "{str(e)}"}}'.encode())
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b'{"error": "Not Found"}')

    def _validate_csrf_token(self, csrf_token):
        # In a real application, you would validate the CSRF token against the user's session
        return csrf_token == 'valid_csrf_token'

def run(server_class=HTTPServer, handler_class=AdminConfigHandler, port=8080):
    server_address = ('', port)
    httpd = server_class(server_address, handler_class)
    print(f'Starting httpd server on port {port}')
    httpd.serve_forever()

if __name__ == '__main__':
    run()