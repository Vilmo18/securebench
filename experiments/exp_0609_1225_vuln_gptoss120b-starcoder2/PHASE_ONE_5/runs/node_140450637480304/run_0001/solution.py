import os
import sqlite3
import xml.etree.ElementTree as ET
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs

UPLOAD_DIR = 'uploads/'
MAX_FILE_SIZE = 2 * 1024 * 1024  # 2 MB
ALLOWED_MIME_TYPES = {'text/csv', 'application/xml'}

def sanitize_filename(filename):
    if os.path.isabs(filename) or '..' in filename or '\x00' in filename:
        return None
    return os.path.basename(filename)

class RequestHandler(BaseHTTPRequestHandler):

    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        data_filename = sanitize_filename(post_data.decode('utf-8').split('\r\n')[0].split(': ')[1])
        config_filename = sanitize_filename(post_data.decode('utf-8').split('\r\n')[1].split(': ')[1])

        if not data_filename or not config_filename:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b'Invalid filename')
            return

        safe_data_path = os.path.join(UPLOAD_DIR, data_filename)
        safe_config_path = os.path.join(UPLOAD_DIR, config_filename)

        with open(safe_data_path, 'wb') as f:
            f.write(post_data.split('\r\n\r\n')[1].split('\r\n\r\n')[0])

        with open(safe_config_path, 'wb') as f:
            f.write(post_data.split('\r\n\r\n')[1].split('\r\n\r\n')[1])

        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'Files uploaded successfully')

    def do_GET(self):
        parsed_path = urlparse(self.path)
        query_params = parse_qs(parsed_path.query)
        report_name = query_params.get('report_name', [None])[0]

        if not report_name:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b'Missing report name')
            return

        data_filename = sanitize_filename(report_name + '.csv')
        config_filename = sanitize_filename(report_name + '.xml')

        if not data_filename or not config_filename:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b'Invalid filename')
            return

        safe_data_path = os.path.join(UPLOAD_DIR, data_filename)
        safe_config_path = os.path.join(UPLOAD_DIR, config_filename)

        if not os.path.exists(safe_data_path) or not os.path.exists(safe_config_path):
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b'Report not found')
            return

        try:
            tree = ET.parse(safe_config_path)
            root = tree.getroot()
        except ET.ParseError:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b'Invalid XML configuration')
            return

        conn = sqlite3.connect(':memory:')
        cursor = conn.cursor()

        with open(safe_data_path, 'r') as f:
            for line in f:
                columns = line.strip().split(',')
                cursor.execute("INSERT INTO report VALUES (?, ?, ?)", columns)

        conn.commit()
        cursor.close()
        conn.close()

        self.send_response(200)
        self.send_header('Content-Disposition', 'attachment; filename="report.txt"')
        self.end_headers()
        with open(safe_data_path, 'r') as f:
            self.wfile.write(f.read().encode())

def run(server_class=HTTPServer, handler_class=RequestHandler):
    server_address = ('', 8000)
    httpd = server_class(server_address, handler_class)
    print('Starting httpd server on port 8000...')
    httpd.serve_forever()

if __name__ == '__main__':
    if not os.path.exists(UPLOAD_DIR):
        os.makedirs(UPLOAD_DIR)
    run()