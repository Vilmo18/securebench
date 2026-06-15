from http.server import BaseHTTPRequestHandler, HTTPServer
import os
import urllib.parse

BASE_DIR = '/var/log/myapp/'
MAX_RESPONSE_SIZE = 1024 * 1024  # 1 MiB

def is_authenticated(handler):
    return 'session_id' in handler.cookies and handler.cookies['session_id'] == 'admin_session'

class LogFileHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        if not is_authenticated(self):
            self.send_response(403)
            self.end_headers()
            return

        parsed_path = urllib.parse.urlparse(self.path)
        query_params = urllib.parse.parse_qs(parsed_path.query)

        log_path = query_params.get('log_path', [None])[0]
        if not log_path:
            self.send_response(400)
            self.end_headers()
            return

        full_path = os.path.join(BASE_DIR, log_path)
        if not full_path.startswith(BASE_DIR) or not os.path.isfile(full_path):
            self.send_response(403)
            self.end_headers()
            return

        try:
            with open(full_path, 'r') as file:
                content = file.read(MAX_RESPONSE_SIZE)

            if len(content) >= MAX_RESPONSE_SIZE:
                content += '\n[Truncated]'

            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(content.encode())
        except FileNotFoundError:
            self.send_response(404)
            self.end_headers()

def run(server_class=HTTPServer, handler_class=LogFileHandler, port=8080):
    server_address = ('', port)
    httpd = server_class(server_address, handler_class)
    print(f'Starting httpd server on port {port}')
    httpd.serve_forever()

if __name__ == '__main__':
    run()