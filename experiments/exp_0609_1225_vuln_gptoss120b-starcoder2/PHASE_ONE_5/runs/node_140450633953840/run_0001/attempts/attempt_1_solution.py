import os
import sqlite3
import xml.etree.ElementTree as ET
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs
import random
import string

# Constants
CONFIG_DIR = 'configs/'
HELPER_DIR = 'helpers/'
DATABASE = 'config.db'
SESSIONS = {}

def generate_csrf_token():
    return ''.join(random.choices(string.ascii_letters + string.digits, k=32))

def sanitize_filename(filename):
    return ''.join(c for c in filename if c.isalnum() or c in ('_', '-'))

class ConfigPortalHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        parsed_path = urlparse(self.path)
        if parsed_path.path == '/list':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            files = os.listdir(CONFIG_DIR)
            self.wfile.write(str(files).encode())
        else:
            self.send_error(404)

    def do_POST(self):
        parsed_path = urlparse(self.path)
        if parsed_path.path == '/upload':
            self.handle_upload()
        elif parsed_path.path == '/apply':
            self.handle_apply()
        else:
            self.send_error(404)

    def handle_upload(self):
        form = parse_qs(self.rfile.read(int(self.headers['Content-Length'])))
        csrf_token = form.get('csrf_token', [None])[0]
        if not csrf_token or csrf_token != SESSIONS.get(self.client_address, {}).get('csrf_token'):
            self.send_error(403)
            return

        file_item = form.get('config.xml')
        if not file_item:
            self.send_error(400)
            return

        filename = sanitize_filename(file_item[0].decode())
        with open(os.path.join(CONFIG_DIR, filename), 'wb') as f:
            f.write(file_item[0])

        self.send_response(200)

    def handle_apply(self):
        form = parse_qs(self.rfile.read(int(self.headers['Content-Length'])))
        csrf_token = form.get('csrf_token', [None])[0]
        filename = form.get('filename', [None])[0]

        if not csrf_token or csrf_token != SESSIONS.get(self.client_address, {}).get('csrf_token'):
            self.send_error(403)
            return

        if not filename:
            self.send_error(400)
            return

        filepath = os.path.join(CONFIG_DIR, sanitize_filename(filename))
        if not os.path.exists(filepath):
            self.send_error(404)
            return

        try:
            tree = ET.parse(filepath)
            root = tree.getroot()
            params = {child.tag: child.text for child in root}

            conn = sqlite3.connect(DATABASE)
            cursor = conn.cursor()
            cursor.execute("INSERT INTO configs VALUES (?, ?)", (filename, str(params)))
            conn.commit()

            helper_content = f"def get_config():\n    return {params}"
            with open(os.path.join(HELPER_DIR, sanitize_filename(filename) + '_helper.py'), 'w') as f:
                f.write(helper_content)

            self.send_response(200)
        except Exception as e:
            self.send_error(500)

def run(server_class=HTTPServer, handler_class=ConfigPortalHandler):
    os.makedirs(CONFIG_DIR, exist_ok=True)
    os.makedirs(HELPER_DIR, exist_ok=True)
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS configs (filename TEXT, content TEXT)")
    server_address = ('', 8000)
    httpd = server_class(server_address, handler_class)
    print('Starting httpd...')
    httpd.serve_forever()

if __name__ == '__main__':
    run()