import os
import uuid
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs

# Constants
UPLOAD_DIR = 'configs'
REPORT_DIR = 'reports'
MAX_FILE_SIZE = 100 * 1024  # 100 KB
ALLOWED_MIME_TYPE = 'application/json'

def sanitize_filename(filename):
    return filename.replace('/', '_').replace('\\', '_')

def validate_json(data):
    if not isinstance(data, dict) or 'title' not in data or not isinstance(data['title'], str) or 'columns' not in data or not isinstance(data['columns'], list):
        return False
    for column in data['columns']:
        if not isinstance(column, dict) or 'name' not in column or not isinstance(column['name'], str):
            return False
    if 'calc' in data:
        for calc in data['calc'].values():
            if not isinstance(calc, dict) or 'expr' not in calc or not isinstance(calc['expr'], str):
                return False
    return True

def generate_report(config_data):
    title = config_data['title']
    columns = config_data['columns']

    html_content = f"<html><head><title>{title}</title></head><body>"
    html_content += f"<h1>{title}</h1>"
    html_content += "<table border='1'>"
    html_content += "<tr>" + "".join(f"<th>{col['name']}</th>" for col in columns) + "</tr>"

    # Simulate some data rows
    for _ in range(5):
        html_content += "<tr>" + "".join(f"<td>{col.get('name', '')}</td>" for col in columns) + "</tr>"

    html_content += "</table></body></html>"
    return html_content

class RequestHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path != '/upload':
            self.send_error(404, 'File Not Found')
            return

        form = parse_qs(urlparse(self.path).query)
        csrf_token = form.get('csrf_token', [None])[0]
        if not csrf_token:
            self.send_response(403, 'Forbidden: Missing CSRF token')
            self.end_headers()
            return

        content_type = self.headers['Content-Type']
        if not content_type.startswith('multipart/form-data'):
            self.send_response(400, 'Bad Request: Invalid Content-Type')
            self.end_headers()
            return

        form_data = {}
        boundary = content_type.split('boundary=')[1]
        parts = self.rfile.read(int(self.headers['Content-Length'])).split(b'--' + boundary.encode())

        for part in parts:
            if not part.strip():
                continue
            headers, body = part.split(b'\r\n\r\n', 1)
            headers_dict = dict([h.decode().split(': ') for h in headers.decode().split('\r\n')])
            form_data[headers_dict['Content-Disposition'].split('name="')[1].split('"')[0]] = body

        config_file = form_data.get('config')
        if not config_file:
            self.send_response(400, 'Bad Request: Missing file')
            self.end_headers()
            return

        filename = sanitize_filename(config_file.decode().split('filename=')[1].strip('"'))
        if not filename.endswith('.json'):
            self.send_response(400, 'Bad Request: Invalid file extension')
            self.end_headers()
            return

        if len(config_file) > MAX_FILE_SIZE:
            self.send_response(413, 'Payload Too Large')
            self.end_headers()
            return

        try:
            config_data = json.loads(config_file)
        except json.JSONDecodeError:
            self.send_response(400, 'Bad Request: Invalid JSON')
            self.end_headers()
            return

        if not validate_json(config_data):
            self.send_response(400, 'Bad Request: Invalid JSON schema')
            self.end_headers()
            return

        unique_filename = str(uuid.uuid4()) + '.json'
        config_path = os.path.join(UPLOAD_DIR, unique_filename)
        with open(config_path, 'wb') as f:
            f.write(config_file)

        report_html = generate_report(config_data)
        report_filename = sanitize_filename(os.path.splitext(filename)[0]) + '.html'
        report_path = os.path.join(REPORT_DIR, report_filename)
        with open(report_path, 'w') as f:
            f.write(report_html)

        self.send_response(200, 'OK')
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        response = {'report_url': f'/reports/{report_filename}'}
        self.wfile.write(json.dumps(response).encode())

def run(server_class=HTTPServer, handler_class=RequestHandler):
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    os.makedirs(REPORT_DIR, exist_ok=True)
    server_address = ('', 8000)
    httpd = server_class(server_address, handler_class)
    print('Starting httpd server on port 8000...')
    httpd.serve_forever()

if __name__ == '__main__':
    run()