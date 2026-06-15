import os
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse
from xml.etree.ElementTree import XMLParser

class SecureXMLParser(XMLParser):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.set_feature(self.FEATURE_EXTERNAL_ENTITIES, False)

def validate_filename(filename):
    base_dir = 'configs/'
    resolved_path = os.path.abspath(os.path.join(base_dir, filename))
    if not resolved_path.startswith(base_dir) or not os.path.isfile(resolved_path):
        return None
    return resolved_path

def run_scan(params):
    # Placeholder for actual scan logic
    return {"status": "success", "message": "Scan completed", "data": params}

def generate_report(params):
    # Placeholder for actual report generation logic
    return {"status": "success", "message": "Report generated", "data": params}

class RequestHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path != '/process':
            self.send_response(404)
            self.end_headers()
            return

        content_type = self.headers['Content-Type']
        if not content_type.startswith('multipart/form-data'):
            self.send_response(400)
            self.end_headers()
            return

        form_data = {}
        boundary = content_type.split('boundary=')[1]
        data = self.rfile.read(int(self.headers['Content-Length'])).decode('utf-8')
        parts = data.split(f'--{boundary}')[1:-1]

        for part in parts:
            headers, body = part.strip().split('\r\n\r\n', 1)
            header_lines = headers.split('\r\n')
            disposition = dict([h.split(': ') for h in header_lines if h.startswith('Content-Disposition')])
            form_data[disposition['name']] = body.strip()

        cmd = form_data.get('cmd')
        filename = form_data.get('filename')
        payload = form_data.get('payload')

        if cmd not in ['scan', 'report']:
            self.send_response(400)
            self.end_headers()
            response = {"status": "error", "message": "Invalid command"}
            self.wfile.write(json.dumps(response).encode('utf-8'))
            return

        resolved_filename = validate_filename(filename)
        if not resolved_filename:
            self.send_response(400)
            self.end_headers()
            response = {"status": "error", "message": "Invalid filename"}
            self.wfile.write(json.dumps(response).encode('utf-8'))
            return

        with open(resolved_filename, 'r') as config_file:
            config_data = config_file.read()

        parser = SecureXMLParser()
        try:
            parser.feed(payload)
            params = {"example_param": "value"}  # Extract parameters from XML
        except Exception as e:
            self.send_response(400)
            self.end_headers()
            response = {"status": "error", "message": f"Invalid payload: {str(e)}"}
            self.wfile.write(json.dumps(response).encode('utf-8'))
            return

        if cmd == 'scan':
            result = run_scan(params)
        elif cmd == 'report':
            result = generate_report(params)

        self.send_response(200)
        self.end_headers()
        response = {"status": "success", "message": "Operation completed successfully", "data": result}
        self.wfile.write(json.dumps(response).encode('utf-8'))

def run(server_class=HTTPServer, handler_class=RequestHandler, port=8080):
    server_address = ('', port)
    httpd = server_class(server_address, handler_class)
    print(f'Starting httpd server on port {port}')
    httpd.serve_forever()

if __name__ == '__main__':
    run()