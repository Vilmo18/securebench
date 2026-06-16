import base64
import pickle
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs
from string import Template
import os

class RenderHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path != '/render':
            self.send_error(400, 'Bad Request')
            return

        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        fields = parse_qs(post_data.decode('utf-8'))

        if 'payload' not in fields:
            self.send_error(400, 'Missing payload')
            return

        try:
            payload_bytes = base64.b64decode(fields['payload'][0])
            data = pickle.loads(payload_bytes)
        except (base64.binascii.Error, pickle.UnpicklingError):
            self.send_error(400, 'Invalid payload')
            return

        if not isinstance(data, dict) or set(data.keys()) != {'template', 'context'}:
            self.send_error(400, 'Invalid data format')
            return

        template_name = data['template']
        context = data['context']

        if not isinstance(template_name, str) or template_name not in {'welcome', 'profile', 'report'}:
            self.send_error(400, 'Invalid template name')
            return

        if not isinstance(context, dict) or not all(isinstance(k, str) and isinstance(v, str) for k, v in context.items()):
            self.send_error(400, 'Invalid context')
            return

        template_path = os.path.join('templates', f'{template_name}.html')

        try:
            with open(template_path, 'r') as file:
                template_content = file.read()
        except FileNotFoundError:
            self.send_error(400, 'Template not found')
            return

        try:
            template = Template(template_content)
            rendered_html = template.substitute(context)
        except KeyError:
            self.send_error(400, 'Context key error')
            return

        self.send_response(200)
        self.send_header('Content-Type', 'text/html')
        self.end_headers()
        self.wfile.write(rendered_html.encode('utf-8'))

def run(server_class=HTTPServer, handler_class=RenderHandler, port=8080):
    server_address = ('', port)
    httpd = server_class(server_address, handler_class)
    httpd.serve_forever()

if __name__ == '__main__':
    run()