import os
import sqlite3
import xml.etree.ElementTree as ET
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs
import secrets

# Constants
CONFIG_DIR = 'configs/'
HELPER_DIR = 'helpers/'
DATABASE = 'config.db'
SESSIONS = {}

def generate_csrf_token():
    return secrets.token_urlsafe(32)

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
        form = parse_qs(self.rfile.read(int(self.headers['Content-Length'])).decode())
        filename = sanitize_filename(form.get('filename', [None])[0])
        if not filename or not filename.endswith('.xml'):
            self.send_error(400, "Invalid filename")
            return

        filepath = os.path.join(CONFIG_DIR, filename)
        with open(filepath, 'wb') as f:
            f.write(form.get('file', [None])[0].encode())

    def handle_apply(self):
        form = parse_qs(self.rfile.read(int(self.headers['Content-Length'])).decode())
        filename = sanitize_filename(form.get('filename', [None])[0])
        if not filename or not filename.endswith('.xml'):
            self.send_error(400, "Invalid filename")
            return

        filepath = os.path.join(CONFIG_DIR, filename)
        if not os.path.exists(filepath):
            self.send_error(404, "File not found")
            return

        try:
            tree = ET.parse(filepath)
            root = tree.getroot()
            params = {child.tag: child.text for child in root}
            # Process the parameters as needed
        except ET.ParseError:
            self.send_error(400, "Invalid XML")

def run(server_class=HTTPServer, handler_class=ConfigPortalHandler):
    server_address = ('', 8000)
    httpd = server_class(server_address, handler_class)
    print('Starting httpd...')
    httpd.serve_forever()

if __name__ == '__main__':
    os.makedirs(CONFIG_DIR, exist_ok=True)
    os.makedirs(HELPER_DIR, exist_ok=True)
    run()