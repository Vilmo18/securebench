import os
import re
from http.server import BaseHTTPRequestHandler, HTTPServer

# Constants
TEMPLATES_DIR = 'templates/'
HELPERS_DIR = 'helpers/'
CSRF_TOKEN_KEY = 'csrf_token'
TEMPLATE_FILE_KEY = 'template_file'
HELPER_MODULE_KEY = 'helper_module'

class TemplateManager(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path != '/admin/template':
            self.send_error(404, "Not Found")
            return

        form = self.rfile.read(int(self.headers['Content-Length'])).decode('utf-8')
        fields = {}
        for field in re.split(r'--.*?\r\n', form):
            if not field:
                continue
            key_value = re.split(r'\r\n', field, 1)
            if len(key_value) < 2:
                continue
            key, value = key_value
            key = re.sub(r'Content-Disposition: form-data; name="(.*)"', r'\1', key).strip()
            value = re.sub(r'\r\n\r\n.*', '', value).strip()
            fields[key] = value

        csrf_token = fields.get(CSRF_TOKEN_KEY)
        if not self._validate_csrf_token(csrf_token):
            self.send_error(403, "Invalid CSRF Token")
            return

        template_file = fields.get(TEMPLATE_FILE_KEY)
        helper_module_name = fields.get(HELPER_MODULE_KEY)

        if not self._validate_template_file(template_file):
            self.send_error(400, "Invalid Template File")
            return

        if not self._validate_helper_module(helper_module_name):
            self.send_error(400, "Invalid Helper Module")
            return

        try:
            with open(os.path.join(TEMPLATES_DIR, template_file), 'wb') as f:
                f.write(self.rfile.read(int(self.headers['Content-Length'])))
        except Exception as e:
            self.send_error(500, str(e))
            return

        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'Template uploaded successfully')

    def _validate_csrf_token(self, csrf_token):
        # Simulate CSRF token validation
        session_csrf_token = 'expected_csrf_token'
        return csrf_token == session_csrf_token

    def _validate_template_file(self, template_file):
        if not template_file:
            return False
        if re.search(r'[./\\]', template_file) or '\0' in template_file:
            return False
        if not template_file.endswith('.html'):
            return False
        return True

    def _validate_helper_module(self, helper_module_name):
        if not helper_module_name:
            return False
        module_path = os.path.join(HELPERS_DIR, f'{helper_module_name}.py')
        if not os.path.isfile(module_path):
            return False
        return True

def run(server_class=HTTPServer, handler_class=TemplateManager, port=8080):
    server_address = ('', port)
    httpd = server_class(server_address, handler_class)
    print(f'Starting httpd server on port {port}')
    httpd.serve_forever()

if __name__ == '__main__':
    run()