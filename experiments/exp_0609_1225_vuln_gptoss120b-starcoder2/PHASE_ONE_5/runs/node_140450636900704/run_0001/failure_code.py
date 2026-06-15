import os
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse

# Constants
CONFIG_DIR = 'configs/'
PROFILE_DIR = 'profiles/'

# Ensure directories exist
os.makedirs(CONFIG_DIR, exist_ok=True)
os.makedirs(PROFILE_DIR, exist_ok=True)

class RequestHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path == '/upload_config':
            self.handle_upload_config()
        elif self.path == '/upload_profile':
            self.handle_upload_profile()
        else:
            self.send_error(404, "File not found")

    def handle_upload_config(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        form = parse_qs(post_data)

        config_file = form.get('config_file')

        if not config_file or len(config_file) != 1:
            self.send_error(400, "Invalid file upload")
            return

        config_file = config_file[0].decode('utf-8')
        filename = os.path.basename(config_file)

        if not filename.endswith('.json'):
            self.send_error(400, "Invalid file type")
            return

        filepath = os.path.join(CONFIG_DIR, filename)
        with open(filepath, 'w') as f:
            json.dump(json.loads(config_file), f)

        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Configuration uploaded successfully")

    def handle_upload_profile(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        form = parse_qs(post_data)

        description_html = form.get('description_html')

        if not description_html or len(description_html) != 1:
            self.send_error(400, "Invalid profile description")
            return

        username = self.client_address[0]
        filename = f"{username}.html"
        filepath = os.path.join(PROFILE_DIR, filename)

        with open(filepath, 'w') as f:
            f.write(description_html[0].decode('utf-8'))

        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Profile description uploaded successfully")

    def do_GET(self):
        parsed_path = urlparse(self.path)
        username = parsed_path.path.strip('/')

        if not username:
            self.send_error(404, "User not found")
            return

        filepath = os.path.join(PROFILE_DIR, f"{username}.html")

        try:
            with open(filepath, 'r') as f:
                content = f.read()
        except FileNotFoundError:
            self.send_error(404, "Profile not found")
            return

        self.send_response(200)
        self.end_headers()
        self.wfile.write(content.encode('utf-8'))

def run(server_class=HTTPServer, handler_class=RequestHandler, port=8080):
    server_address = ('', port)
    httpd = server_class(server_address, handler_class)
    print(f"Starting httpd server on port {port}")
    httpd.serve_forever()

if __name__ == '__main__':
    run()