import os
import re
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse
from markupsafe import escape

UPLOAD_DIR = 'uploads/'
REPORT_DIR = 'reports/'

def validate_filename(filename):
    return bool(re.match(r'^[a-zA-Z0-9-_]+\.md$', filename))

class RequestHandler(BaseHTTPRequestHandler):

    def do_POST(self):
        if not self.verify_csrf_token():
            self.send_error(403, 'Invalid CSRF token')
            return

        if not self.is_authenticated_employee():
            self.send_error(403, 'Authentication failed')
            return

        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        boundary = self.headers['Content-Type'].split('boundary=')[-1]
        parts = post_data.split(b'--' + boundary.encode())

        for part in parts:
            if b'name="report.md"' in part:
                filename = re.search(r'filename="(.+?)"', part.decode()).group(1)
                if not validate_filename(filename):
                    self.send_error(400, 'Invalid filename')
                    return

                file_content = re.search(r'\r\n\r\n(.+)\r\n', part.decode(), re.DOTALL).group(1)

                safe_path = os.path.join(UPLOAD_DIR, filename)
                with open(safe_path, 'w') as f:
                    f.write(file_content)

                html_content = escape(file_content)
                html_filename = filename.replace('.md', '.html')
                safe_html_path = os.path.join(REPORT_DIR, html_filename)
                with open(safe_html_path, 'w') as f:
                    f.write(html_content)

                self.send_response(201)
                self.end_headers()
                return

        self.send_error(400, 'Invalid request')

    def do_GET(self):
        parsed_path = urlparse(self.path)
        filename = os.path.basename(parsed_path.path)
        safe_html_path = os.path.join(REPORT_DIR, filename)

        if not os.path.isfile(safe_html_path):
            self.send_error(404, 'File not found')
            return

        with open(safe_html_path, 'r') as f:
            html_content = f.read()

        self.send_response(200)
        self.send_header('Content-Type', 'text/html')
        self.send_header('Content-Disposition', 'inline')
        self.end_headers()
        self.wfile.write(html_content.encode())

    def verify_csrf_token(self):
        return True  # Implement CSRF token verification

    def is_authenticated_employee(self):
        return True  # Implement user authentication and role check

def run(server_class=HTTPServer, handler_class=RequestHandler, port=8080):
    server_address = ('', port)
    httpd = server_class(server_address, handler_class)
    print(f'Starting httpd server on port {port}')
    httpd.serve_forever()

if __name__ == '__main__':
    run()