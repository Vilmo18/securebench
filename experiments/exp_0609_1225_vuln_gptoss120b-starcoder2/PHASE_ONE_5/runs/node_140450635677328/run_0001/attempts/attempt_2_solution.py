import os
import re
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs
from io import BytesIO
from html.parser import HTMLParser
import json
import ast

class SafeEvaluator:
    def __init__(self, user):
        self.user = user

    def evaluate(self, expr):
        try:
            # Simple arithmetic and attribute lookup
            if re.match(r'^[\w.+\-*/() ]+$', expr):
                node = ast.parse(expr, mode='eval')
                for n in ast.walk(node):
                    if isinstance(n, ast.Name) and n.id not in self.user:
                        raise ValueError("Invalid expression")
                return eval(compile(node, '<string>', 'eval'), {"__builtins__": None}, {"user": self.user})
            else:
                raise ValueError("Invalid expression")
        except Exception as e:
            raise ValueError(f"Evaluation error: {e}")

class FileUploadHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path == '/upload-template':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            form = parse_qs(post_data, keep_blank_values=1)

            if 'template' not in form:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b'Missing template file')
                return

            uploaded_file = form['template'][0]
            filename = uploaded_file[uploaded_file.find('filename=') + 9:].strip('"')

            if not filename.endswith('.html') or len(uploaded_file) > 102400:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b'Invalid file type or size')
                return

            try:
                content = uploaded_file.split(b'\r\n\r\n', 1)[1]
                if b'<!DOCTYPE' in content or b'<?xml' in content:
                    raise ValueError("Invalid HTML content")

                placeholders = re.findall(r'{{\s*([^}]+)\s*}}', content.decode())
                for placeholder in placeholders:
                    evaluator = SafeEvaluator({'age': 25, 'name': 'John Doe'})
                    try:
                        result = evaluator.evaluate(placeholder)
                        if not isinstance(result, (int, str)):
                            raise ValueError("Invalid expression result")
                    except ValueError as e:
                        self.send_response(400)
                        self.end_headers()
                        self.wfile.write(str(e).encode())
                        return

                sanitized_filename = re.sub(r'[^a-zA-Z0-9_.]', '_', filename)
                safe_path = os.path.join('templates', sanitized_filename)
                with open(safe_path, 'wb') as f:
                    f.write(content)

                response = {'filename': sanitized_filename, 'status': 'success'}
                self.send_response(200)
                self.end_headers()
                self.wfile.write(bytes(json.dumps(response), 'utf-8'))
            except Exception as e:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(str(e).encode())
        else:
            self.send_response(404)
            self.end_headers()

def run(server_class=HTTPServer, handler_class=FileUploadHandler, port=8080):
    server_address = ('', port)
    httpd = server_class(server_address, handler_class)
    print(f'Starting httpd server on port {port}')
    httpd.serve_forever()

if __name__ == '__main__':
    run()