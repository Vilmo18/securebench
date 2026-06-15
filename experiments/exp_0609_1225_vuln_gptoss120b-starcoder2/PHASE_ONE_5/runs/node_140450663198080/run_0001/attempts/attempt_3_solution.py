import os
import json
import re
from http.server import BaseHTTPRequestHandler, HTTPServer

CONFIG_DIR = 'configs/'
REPORTS_DIR = 'reports/'

def validate_filename(filename):
    return re.match(r'^[a-zA-Z0-9-_]+\.json$', filename) is not None

def save_config_file(config_name, file_content):
    if not os.path.exists(CONFIG_DIR):
        os.makedirs(CONFIG_DIR)
    safe_path = os.path.abspath(os.path.join(CONFIG_DIR, config_name))
    if not safe_path.startswith(os.path.abspath(CONFIG_DIR)):
        raise ValueError("Invalid path")
    with open(safe_path, 'wb') as f:
        f.write(file_content)

def load_config_file(config_name):
    try:
        safe_path = os.path.abspath(os.path.join(CONFIG_DIR, config_name))
        if not safe_path.startswith(os.path.abspath(CONFIG_DIR)):
            raise ValueError("Invalid path")
        with open(safe_path, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        raise ValueError("Invalid configuration file") from e

def sanitize_output_name(title):
    return re.sub(r'[^a-zA-Z0-9-_]', '_', title)

class RequestHandler(BaseHTTPRequestHandler):

    def do_POST(self):
        if self.path == '/upload':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            form = post_data.decode('utf-8')
            filename_match = re.search(r'filename="(.+?)"', form)
            if not filename_match or not validate_filename(filename_match.group(1)):
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b"Invalid filename")
                return

            config_name = filename_match.group(1)
            boundary_match = re.search(r'--(.+?)$', form, re.DOTALL)
            if not boundary_match:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b"Invalid file content")
                return
            file_content = boundary_match.group(1).encode('utf-8')
            save_config_file(config_name, file_content)

            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"Configuration uploaded successfully")

        elif self.path.startswith('/generate'):
            config_name = self.path.split('=')[1]
            try:
                config = load_config_file(config_name)
                title = config['title']
                date_range = config['date_range']

                output_name = sanitize_output_name(title)
                reports_path = os.path.abspath(os.path.join(REPORTS_DIR, f"{output_name}.pdf"))
                if not reports_path.startswith(os.path.abspath(REPORTS_DIR)):
                    raise ValueError("Invalid path")

                if not os.path.exists(REPORTS_DIR):
                    os.makedirs(REPORTS_DIR)

                cmd = ['reportgen', '--title', title, '--date', date_range, '--output', reports_path]
                os.execvpe('reportgen', cmd, {})

                self.send_response(200)
                self.end_headers()
                self.wfile.write(reports_path.encode('utf-8'))

            except ValueError as e:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(str(e).encode('utf-8'))

def run(server_class=HTTPServer, handler_class=RequestHandler):
    server_address = ('', 8000)
    httpd = server_class(server_address, handler_class)
    print("Starting httpd server on port 8000...")
    httpd.serve_forever()

if __name__ == '__main__':
    run()