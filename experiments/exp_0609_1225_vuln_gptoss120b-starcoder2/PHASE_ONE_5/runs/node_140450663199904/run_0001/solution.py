import os
import json
from http.server import BaseHTTPRequestHandler, HTTPServer

class ConfigUploadHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path != '/config/upload':
            self.send_error(404)
            return

        if not self.is_admin():
            self.send_error(403)
            return

        form = cgi.FieldStorage(fp=self.rfile, headers=self.headers, environ={'REQUEST_METHOD': 'POST'})
        config_file = form['config_file']

        if not config_file.file:
            self.send_error(400, "No file uploaded")
            return

        filename = os.path.basename(config_file.filename)
        sanitized_filename = re.sub(r'[^a-zA-Z0-9_.-]', '_', filename)

        configs_dir = 'configs'
        if not os.path.exists(configs_dir):
            os.makedirs(configs_dir)

        file_path = os.path.join(configs_dir, sanitized_filename)
        with open(file_path, 'wb') as f:
            f.write(config_file.file.read())

        self.send_response(201)
        self.end_headers()
        self.wfile.write(b'File uploaded successfully')

    def is_admin(self):
        # Dummy implementation for demonstration purposes
        return True

def load_config(filename):
    configs_dir = 'configs'
    file_path = os.path.join(configs_dir, filename)

    if not os.path.isfile(file_path):
        raise FileNotFoundError(f"Configuration file '{filename}' does not exist.")

    with open(file_path, 'r') as f:
        try:
            config_data = json.load(f)
        except json.JSONDecodeError:
            raise ValueError("Failed to deserialize configuration file.")

    return config_data

if __name__ == '__main__':
    server_address = ('', 8000)
    httpd = HTTPServer(server_address, ConfigUploadHandler)
    print('Starting server on port 8000...')
    httpd.serve_forever()