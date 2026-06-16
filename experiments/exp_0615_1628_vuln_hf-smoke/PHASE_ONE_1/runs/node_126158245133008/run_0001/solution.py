import os
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs

class SecureFileDownloadHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path.startswith('/download'):
            query_components = parse_qs(urlparse(self.path).query)
            file_path = query_components.get('file', [None])[0]
            
            if file_path is None:
                self.send_error(404, 'File not specified')
                return
            
            base_dir = os.path.abspath('files/')
            requested_path = os.path.abspath(os.path.join(base_dir, file_path))
            
            if not requested_path.startswith(base_dir):
                self.send_error(404, 'Invalid file path')
                return
            
            if not os.path.isfile(requested_path):
                self.send_error(404, 'File not found')
                return
            
            try:
                with open(requested_path, 'rb') as file:
                    content = file.read()
            except IOError:
                self.send_error(404, 'File could not be read')
                return
            
            mime_type = self.guess_mime_type(requested_path)
            self.send_response(200)
            self.send_header('Content-Type', mime_type)
            self.end_headers()
            self.wfile.write(content)
        else:
            self.send_error(404, 'Endpoint not found')

    def guess_mime_type(self, path):
        if path.endswith('.txt'):
            return 'text/plain'
        elif path.endswith('.html'):
            return 'text/html'
        elif path.endswith('.jpg') or path.endswith('.jpeg'):
            return 'image/jpeg'
        elif path.endswith('.png'):
            return 'image/png'
        elif path.endswith('.gif'):
            return 'image/gif'
        elif path.endswith('.pdf'):
            return 'application/pdf'
        else:
            return 'application/octet-stream'

def run(server_class=HTTPServer, handler_class=SecureFileDownloadHandler, port=8000):
    server_address = ('', port)
    httpd = server_class(server_address, handler_class)
    httpd.serve_forever()

if __name__ == '__main__':
    run()