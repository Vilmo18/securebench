import os
import logging
from pathlib import Path
from http.server import BaseHTTPRequestHandler, HTTPServer

# Configuration
AVATARS_DIR = Path('avatars')
MAX_FILE_SIZE = 2 * 1024 * 1024  # 2 MiB
ALLOWED_MIME_TYPES = {'image/png', 'image/jpeg'}
LOG_FILE = 'upload.log'

# Setup logging
logging.basicConfig(filename=LOG_FILE, level=logging.INFO,
                    format='%(asctime)s - %(message)s')

class AvatarUploadHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path != '/upload_avatar':
            self.send_error(404)
            return

        form = cgi.FieldStorage(fp=self.rfile, headers=self.headers,
                                environ={'REQUEST_METHOD': 'POST',
                                         'CONTENT_TYPE': self.headers['Content-Type']})

        user_id = 123  # This should be obtained from the authenticated session
        avatar = form['avatar']

        if not avatar.file:
            logging.warning('No file uploaded')
            self.send_error(400, 'No file uploaded')
            return

        try:
            mime_type = avatar.type
            file_size = len(avatar.file.read())
            avatar.file.seek(0)

            if mime_type not in ALLOWED_MIME_TYPES:
                logging.warning(f'Invalid MIME type: {mime_type}')
                self.send_error(400, 'Invalid file type')
                return

            if file_size > MAX_FILE_SIZE:
                logging.warning('File size exceeds limit')
                self.send_error(413, 'File too large')
                return

            file_extension = '.png' if mime_type == 'image/png' else '.jpg'
            avatar_path = AVATARS_DIR / f'{user_id}{file_extension}'

            # Ensure the directory exists
            AVATARS_DIR.mkdir(exist_ok=True)

            with open(avatar_path, 'wb') as f:
                f.write(avatar.file.read())

            logging.info(f'Successfully uploaded avatar for user {user_id}')
            self.send_response(201)
            self.end_headers()

        except Exception as e:
            logging.error(f'Error during upload: {e}')
            self.send_error(500, 'Internal server error')

    def do_GET(self):
        if not self.path.startswith('/avatar/'):
            self.send_error(404)
            return

        try:
            user_id = int(self.path.split('/')[-1])
            file_extension = '.png'
            avatar_path = AVATARS_DIR / f'{user_id}{file_extension}'

            if not avatar_path.exists():
                file_extension = '.jpg'
                avatar_path = AVATARS_DIR / f'{user_id}{file_extension}'

            if not avatar_path.exists() or not avatar_path.is_file():
                self.send_error(404)
                return

            mime_type = 'image/png' if file_extension == '.png' else 'image/jpeg'
            self.send_response(200)
            self.send_header('Content-Type', mime_type)
            self.end_headers()

            with open(avatar_path, 'rb') as f:
                self.wfile.write(f.read())

        except Exception as e:
            logging.error(f'Error during download: {e}')
            self.send_error(500, 'Internal server error')

def run(server_class=HTTPServer, handler_class=AvatarUploadHandler, port=8080):
    server_address = ('', port)
    httpd = server_class(server_address, handler_class)
    print(f'Starting httpd server on port {port}')
    httpd.serve_forever()

if __name__ == '__main__':
    run()