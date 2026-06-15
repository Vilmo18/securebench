import os
import defusedxml.ElementTree as ET
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs
import subprocess

# Hard-coded credentials for simplicity
CREDENTIALS = {
    'user1': 'password1',
    'user2': 'password2'
}

# Role to directory mapping (loaded from XML)
ROLE_DIRS = {}

# Session token to role mapping
SESSION_TOKENS = {}
TOKEN_COUNTER = 0

def load_role_dirs():
    global ROLE_DIRS
    tree = ET.parse('role_dirs.xml')
    root = tree.getroot()
    for role in root.findall('role'):
        dir_path = role.text.strip()
        ROLE_DIRS[role.attrib['name']] = dir_path

def authenticate(username, password):
    if username in CREDENTIALS and CREDENTIALS[username] == password:
        global TOKEN_COUNTER
        token = f'token{TOKEN_COUNTER}'
        SESSION_TOKENS[token] = username
        TOKEN_COUNTER += 1
        return token
    else:
        raise ValueError('Invalid credentials')

def validate_filename(filename):
    if not filename.endswith('.conf') or not all(c.isalnum() or c in '_-' for c in filename[:-5]):
        raise ValueError('Invalid filename')

class RequestHandler(BaseHTTPRequestHandler):

    def do_POST(self):
        parsed_path = urlparse(self.path)
        if parsed_path.path == '/login':
            self.login()
        else:
            self.send_error(404, 'Not Found')

    def login(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length).decode('utf-8')
        username, password = post_data.split('&')
        username = parse_qs(username)[0]
        password = parse_qs(password)[0]

        try:
            token = authenticate(username, password)
            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(token.encode())
        except ValueError as e:
            self.send_error(401, str(e))

    def do_GET(self):
        parsed_path = urlparse(self.path)
        if parsed_path.path == '/fetch':
            self.fetch_file()
        else:
            self.send_error(404, 'Not Found')

    def fetch_file(self):
        token = self.headers.get('token')
        query_components = parse_qs(urlparse(self.path).query)
        filename = query_components['filename'][0]

        try:
            username = SESSION_TOKENS[token]
            role = username  # Assuming username == role for simplicity
            if role not in ROLE_DIRS:
                raise ValueError('Unauthorized access')

            validate_filename(filename)

            dir_path = ROLE_DIRS[role]
            file_path = os.path.join(dir_path, filename)
            if not file_path.startswith(dir_path):
                raise ValueError('Invalid path')

            with open(file_path, 'rb') as f:
                compressed_data = subprocess.run(['gzip', '-c', file_path], stdout=subprocess.PIPE).stdout

            self.send_response(200)
            self.send_header('Content-type', 'application/octet-stream')
            self.end_headers()
            self.wfile.write(compressed_data)

        except KeyError:
            self.send_error(401, 'Unauthorized access')
        except ValueError as e:
            self.send_error(400, str(e))
        except FileNotFoundError:
            self.send_error(404, 'File not found')

def run(server_class=HTTPServer, handler_class=RequestHandler):
    server_address = ('', 8000)
    httpd = server_class(server_address, handler_class)
    load_role_dirs()
    print('Starting httpd server on port 8000...')
    httpd.serve_forever()

if __name__ == '__main__':
    run()