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
        boundary = self.headers['Content-Type'].split('boundary=')[1].encode()

        parts = post_data.split(boundary)
        data_file = None
        config_file = None

        for part in parts:
            if b'name="data_file"' in part:
                data_file = part.split(b'\r\n\r\n')[1].split(b'\r\n--')[0]
            elif b'name="config_file"' in part:
                config_file = part.split(b'\r\n\r\n')[1].split(b'\r\n--')[0]

        if not data_file or not config_file:
            self.send_error(400, 'Missing file')
            return

        data_filename = sanitize_filename(self.headers['Content-Disposition'].split('filename="')[1].split('"')[0])
        config_filename = sanitize_filename(self.headers['Content-Disposition'].split('filename="')[1].split('"')[0])

        if not data_filename or not config_filename:
            self.send_error(400, 'Invalid filename')
            return

        if len(data_file) > MAX_FILE_SIZE or len(config_file) > MAX_FILE_SIZE:
            self.send_error(400, 'File too large')
            return

        safe_data_path = os.path.join(UPLOAD_DIR, data_filename)
        safe_config_path = os.path.join(UPLOAD_DIR, config_filename)

        with open(safe_data_path, 'wb') as f:
            f.write(data_file)

        with open(safe_config_path, 'wb') as f:
            f.write(config_file)

        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'Files uploaded successfully')

    def do_GET(self):
        parsed_path = urlparse(self.path)
        query_params = parse_qs(parsed_path.query)
        report_name = query_params.get('report_name', [None])[0]

        if not report_name:
            self.send_error(400, 'Missing report name')
            return

        data_filename = sanitize_filename(report_name + '.csv')
        config_filename = sanitize_filename(report_name + '.xml')

        if not data_filename or not config_filename:
            self.send_error(400, 'Invalid filename')
            return

        safe_data_path = os.path.join(UPLOAD_DIR, data_filename)
        safe_config_path = os.path.join(UPLOAD_DIR, config_filename)

        if not os.path.exists(safe_data_path) or not os.path.exists(safe_config_path):
            self.send_error(404, 'Report not found')
            return

        try:
            tree = ET.parse(safe_config_path)
            root = tree.getroot()
        except ET.ParseError:
            self.send_error(400, 'Invalid XML configuration')
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