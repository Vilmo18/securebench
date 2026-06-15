import os
import re
from http.server import BaseHTTPRequestHandler, HTTPServer

UPLOAD_DIR = 'user_images'
ALLOWED_EXTENSIONS = {'.png', '.jpg', '.jpeg'}
USERNAME_REGEX = re.compile(r'^[a-zA-Z0-9_]+$')

def is_valid_filename(filename):
    return any(filename.lower().endswith(ext) for ext in ALLOWED_EXTENSIONS)

def sanitize_filename(filename):
    return re.sub(r'[^a-zA-Z0-9_.]', '_', filename)

class RequestHandler(BaseHTTPRequestHandler):

    def do_POST(self):
        if self.path != '/upload':
            self.send_error(404)
            return

        form = {}
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length).decode('utf-8')

        for field in post_data.split('&'):
            key, value = field.split('=')
            form[key] = value.replace('+', ' ')

        username = form.get('username')
        avatar = form.get('avatar')

        if not username or not USERNAME_REGEX.match(username):
            self.send_error(400, 'Invalid username')
            return

        if not avatar:
            self.send_error(400, 'No file uploaded')
            return

        filename = sanitize_filename(os.path.basename(avatar))
        if not is_valid_filename(filename):
            self.send_error(400, 'Unsupported file type')
            return

        safe_path = os.path.join(UPLOAD_DIR, f"{username}_{filename}")
        if not safe_path.startswith(UPLOAD_DIR + os.sep):
            self.send_error(400, 'Invalid path')
            return

        try:
            os.makedirs(UPLOAD_DIR, exist_ok=True)
            with open(safe_path, 'wb') as f:
                f.write(self.rfile.read(content_length))
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'File uploaded successfully')
        except Exception as e:
            self.send_error(500, str(e))

def run(server_class=HTTPServer, handler_class=RequestHandler, port=8080):
    server_address = ('', port)
    httpd = server_class(server_address, handler_class)
    print(f'Starting httpd server on port {port}')
    httpd.serve_forever()

if __name__ == '__main__':
    run()