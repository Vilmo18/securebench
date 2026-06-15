import os
import json
from pathlib import Path, PurePath
import subprocess
from http.server import BaseHTTPRequestHandler, HTTPServer

class ConvertHandler(BaseHTTPRequestHandler):
    ALLOWED_FORMATS = {'pdf', 'txt', 'md'}
    UPLOAD_DIR = Path('/var/app/uploads/')
    OUTPUT_DIR = Path('/var/app/outputs/')

    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        data = json.loads(post_data)

        source_path_str = data.get('source_path')
        target_format = data.get('target_format')

        if not isinstance(source_path_str, str) or not isinstance(target_format, str):
            self.send_error(400, 'Invalid input type')
            return

        try:
            source_path = Path(PurePath(source_path_str))
        except (ValueError, TypeError):
            self.send_error(400, 'Invalid source path')
            return

        if not (source_path.is_absolute() and
                source_path.exists() and
                source_path.is_file() and
                source_path.resolve().is_relative_to(self.UPLOAD_DIR)):
            self.send_error(400, 'Invalid source path')
            return

        if target_format not in self.ALLOWED_FORMATS:
            self.send_error(400, 'Invalid target format')
            return

        output_path = self.OUTPUT_DIR / (source_path.stem + '.' + target_format)
        command = ["/usr/local/bin/convert_file", str(source_path), str(output_path)]

        try:
            subprocess.run(command, shell=False, check=True)
            response = json.dumps({"output_path": str(output_path)})
        except subprocess.CalledProcessError as e:
            response = json.dumps({"error": "Conversion failed"})
        except Exception as e:
            response = json.dumps({"error": str(e)})

        self.send_response(200 if 'error' not in response else 400)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(response.encode())

def run(server_class=HTTPServer, handler_class=ConvertHandler, port=8080):
    server_address = ('', port)
    httpd = server_class(server_address, handler_class)
    print(f'Starting httpd server on port {port}')
    httpd.serve_forever()

if __name__ == '__main__':
    run()