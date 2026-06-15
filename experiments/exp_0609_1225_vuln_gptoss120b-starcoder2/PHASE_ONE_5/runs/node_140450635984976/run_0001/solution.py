from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import base64
import xml.etree.ElementTree as ET
from defusedxml.elementtree import fromstring

class RequestHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path == '/process':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            try:
                data = json.loads(post_data)

                # Decode and validate settings
                settings_base64 = data.get('settings')
                settings_bytes = base64.b64decode(settings_base64)
                settings = json.loads(settings_bytes.decode('utf-8'))
                if not isinstance(settings, dict) or not all(isinstance(k, str) and isinstance(v, (str, int, float, bool)) for k, v in settings.items()):
                    self.send_response(400)
                    self.end_headers()
                    self.wfile.write(b'Invalid settings')
                    return

                # Process template
                template = data.get('template', '')
                allowed_vars = {k: str(v) for k, v in settings.items()}
                resolved_template = template.format(**allowed_vars)

                # Parse XML data safely
                xml_data = data.get('xml_data', '')
                tree = ET.ElementTree(fromstring(xml_data))
                root = tree.getroot()
                value_element = root.find('.//{*}value')
                extracted_value = value_element.text if value_element is not None else None

                response = {
                    'resolved_template': resolved_template,
                    'extracted_value': extracted_value
                }

                self.send_response(200)
                self.end_headers()
                self.wfile.write(json.dumps(response).encode('utf-8'))

            except (json.JSONDecodeError, base64.binascii.Error, ET.ParseError) as e:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(str(e).encode('utf-8'))
        else:
            self.send_response(404)
            self.end_headers()

def run(server_class=HTTPServer, handler_class=RequestHandler, port=8080):
    server_address = ('', port)
    httpd = server_class(server_address, handler_class)
    print(f'Starting httpd server on port {port}')
    httpd.serve_forever()

if __name__ == '__main__':
    run()