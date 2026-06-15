import os
from http.server import HTTPServer, BaseHTTPRequestHandler
import urllib.parse as urlparse

UPLOAD_DIR = "avatars"
ALLOWED_MIME_TYPES = {"image/png", "image/jpeg"}

def sanitize_filename(filename):
    return ''.join(c if c.isalnum() or c in {'-', '_', '.'} else '' for c in filename)

class AvatarHandler(BaseHTTPRequestHandler):

    def do_POST(self):
        if self.path == '/upload':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            boundary = self.headers['Content-Type'].split('boundary=')[-1]
            parts = post_data.split(b'--' + boundary.encode())[1].split(b'\r\n')[0].decode().strip()

            if not parts.startswith('Content-Disposition: form-data; name="avatar"; filename='):
                self.send_error(400, "Invalid form data")
                return

            filename = parts.split('filename=')[-1].strip('"')
            sanitized_filename = sanitize_filename(filename)

            if not sanitized_filename:
                self.send_error(400, "Invalid file name")
                return

            file_data_start = post_data.index(b'\r\n\r\n') + 4
            file_data = post_data[file_data_start:]

            mime_type = None
            with open(sanitized_filename, 'rb') as f:
                mime_type = f.read(26)

            if not any(mime_type.startswith(prefix.encode()) for prefix in ALLOWED_MIME_TYPES):
                self.send_error(400, "Invalid file type")
                return

            file_path = os.path.join(UPLOAD_DIR, sanitized_filename)
            with open(file_path, 'wb') as f:
                f.write(file_data)

            self.send_response(201)
            self.end_headers()
        else:
            self.send_error(405, "Method not allowed")

    def do_GET(self):
        parsed_path = urlparse.urlparse(self.path)
        username = parsed_path.path.split('/')[-1]

        file_path = os.path.join(UPLOAD_DIR, sanitize_filename(username))
        if not os.path.exists(file_path):
            self.send_error(404, "File not found")
            return

        with open(file_path, 'rb') as f:
            content_type = None
            mime_type = f.read(26)
            if mime_type.startswith(b'\x89PNG'):
                content_type = 'image/png'
            elif mime_type.startswith(b'\xff\xd8\xff'):
                content_type = 'image/jpeg'

        self.send_response(200)
        self.send_header('Content-Type', content_type)
        self.end_headers()
        with open(file_path, 'rb') as f:
            self.wfile.write(f.read())

def run(server_class=HTTPServer, handler_class=AvatarHandler):
    server_address = ('', 8000)
    httpd = server_class(server_address, handler_class)
    print("Starting httpd server on port 8000...")
    httpd.serve_forever()

if __name__ == '__main__':
    run()