import os
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs

class ConfigHandler(BaseHTTPRequestHandler):
    CONFIG_DIR = 'configs'

    def do_POST(self):
        if self.path != '/upload':
            self.send_error(404)
            return

        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)

        try:
            config_dict = json.loads(post_data)
        except json.JSONDecodeError:
            self.send_error(400, 'Invalid JSON data')
            return

        if not isinstance(config_dict, dict) or 'name' not in config_dict or 'settings' not in config_dict:
            self.send_error(400, 'Invalid configuration format')
            return

        name = config_dict['name']
        settings = config_dict['settings']

        if not isinstance(name, str) or not isinstance(settings, dict):
            self.send_error(400, 'Invalid configuration types')
            return

        if not self.is_valid_filename(name):
            self.send_error(400, 'Invalid filename')
            return

        file_path = os.path.join(self.CONFIG_DIR, f'{name}.json')

        try:
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, 'w') as f:
                json.dump(settings, f)
        except IOError:
            self.send_error(500, 'Failed to write configuration file')
            return

        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'Configuration uploaded successfully')

    def do_GET(self):
        if self.path != '/download':
            self.send_error(404)
            return

        query_components = parse_qs(urlparse(self.path).query)
        file_name = query_components.get('file', [None])[0]

        if not file_name or not self.is_valid_filename(file_name):
            self.send_error(400, 'Invalid filename')
            return

        file_path = os.path.join(self.CONFIG_DIR, f'{file_name}.json')

        if not os.path.isfile(file_path):
            self.send_error(404, 'File not found')
            return

        try:
            with open(file_path, 'r') as f:
                config_content = f.read()
        except IOError:
            self.send_error(500, 'Failed to read configuration file')
            return

        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(config_content.encode())

    @staticmethod
    def is_valid_filename(filename):
        if not all(c.isalnum() or c in '-_' for c in filename):
            return False
        if os.path.sep in filename or os.pardir in filename or '\x00' in filename:
            return False
        return True

def run(server_class=HTTPServer, handler_class=ConfigHandler, port=8080):
    server_address = ('', port)
    httpd = server_class(server_address, handler_class)
    httpd.serve_forever()

if __name__ == '__main__':
    run()