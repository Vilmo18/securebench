import os
import re
import subprocess
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from xml.etree.ElementTree import XMLParser

ALLOWED_FILENAME_CHARS = re.compile(r'^[a-zA-Z0-9._-]+$')
WHITELISTED_COMMANDS = {'apply', 'reset', 'status'}
CONFIG_DIR = 'configs/'

class SecureXMLParser(XMLParser):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._target_element = None

    def start(self, tag, attrs):
        if tag == 'script':
            self._target_element = []

    def end(self, tag):
        if tag == 'script' and self._target_element:
            return b''.join(self._target_element).decode()

    def data(self, data):
        if self._target_element is not None:
            self._target_element.append(data)

class ConfigHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers['Content-Length'])
        form_data = self.rfile.read(length)
        boundary = self.headers['Content-Type'].split('boundary=')[1].encode()

        parts = form_data.split(boundary)
        for part in parts:
            if b'config_file' in part:
                filename_bytes = re.search(b'filename="(.+?)"', part)
                if not filename_bytes:
                    self.send_error(400, 'Invalid file upload')
                    return

                filename = filename_bytes.group(1).decode()
                if not ALLOWED_FILENAME_CHARS.match(filename) or \
                   os.path.isabs(filename) or '..' in filename.split(os.sep):
                    self.send_error(400, 'Invalid filename')
                    return

                config_path = os.path.join(CONFIG_DIR, filename)
                if not os.path.exists(CONFIG_DIR):
                    os.makedirs(CONFIG_DIR)

                content_disposition = part.split(b'\r\n\r\n')[0]
                file_content_start = part.find(b'\r\n\r\n') + 4
                file_content = part[file_content_start:]

                with open(config_path, 'wb') as f:
                    f.write(file_content)

                parser = SecureXMLParser()
                try:
                    parser.feed(open(config_path, 'rb').read())
                    command = parser.close().strip()
                except Exception as e:
                    self.send_error(500, str(e))
                    return

                if command not in WHITELISTED_COMMANDS:
                    self.send_error(400, 'Invalid command')
                    return

                try:
                    result = subprocess.run([command], capture_output=True, text=True)
                    response_content = {
                        'stdout': result.stdout,
                        'success': True
                    }
                except Exception as e:
                    response_content = {'error': str(e), 'success': False}

                self.send_response(200 if response_content['success'] else 500)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(bytes(json.dumps(response_content), 'utf-8'))
                return

def run(server_class=HTTPServer, handler_class=ConfigHandler):
    server_address = ('', 8000)
    httpd = server_class(server_address, handler_class)
    print('Starting httpd server on port 8000...')
    httpd.serve_forever()

if __name__ == '__main__':
    run()