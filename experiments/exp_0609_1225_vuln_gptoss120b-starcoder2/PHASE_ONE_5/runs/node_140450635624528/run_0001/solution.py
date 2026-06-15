import json
import pickle
from http.server import BaseHTTPRequestHandler, HTTPServer
from io import BytesIO
from urllib.parse import parse_qs
from xml.etree.ElementTree import XMLParser, ParseError
import math

# JSON schema validation
def validate_json(data):
    required_fields = {'name', 'version'}
    if not all(field in data for field in required_fields):
        return False, "Missing required fields"
    if not isinstance(data.get('name'), str) or not isinstance(data.get('version'), str):
        return False, "Invalid type for required fields"
    if 'legacy_xml' in data and not isinstance(data['legacy_xml'], str):
        return False, "Invalid type for legacy_xml"
    if 'calc_expr' in data and not isinstance(data['calc_expr'], str):
        return False, "Invalid type for calc_expr"
    return True, ""

# Secure XML parser
class SafeXMLParser(XMLParser):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.set_feature(feature_xml_entities, False)

def parse_safe_xml(xml_str):
    try:
        parser = SafeXMLParser()
        parser.feed(xml_str)
        return True
    except ParseError as e:
        return False

# Expression compiler with restrictions
allowed_names = {name for name in dir(math) if not name.startswith('_')}
allowed_operators = {'+', '-', '*', '/', '(', ')', 'math.'}

def compile_expression(expr):
    try:
        compiled_expr = compile(expr, '<string>', 'eval')
        code = compiled_expr.co_code
        for op in allowed_operators:
            if op not in expr:
                return False, "Invalid operator or function"
        for name in compiled_expr.co_names:
            if name not in allowed_names:
                return False, "Invalid function"
        return True, lambda x: eval(expr)
    except SyntaxError:
        return False, "Syntax error"

# Pickle serialization with type check
def serialize_config(config):
    def is_primitive(obj):
        if isinstance(obj, (str, int, float, bool)):
            return True
        elif isinstance(obj, dict):
            return all(is_primitive(k) and is_primitive(v) for k, v in obj.items())
        elif isinstance(obj, list):
            return all(is_primitive(item) for item in obj)
        return False

    if not is_primitive(config):
        return False
    return pickle.dumps(config)

class ConfigHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_type = self.headers['Content-Type']
        if 'multipart/form-data' not in content_type:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b"Invalid Content-Type")
            return

        boundary = content_type.split('boundary=')[1]
        form_data = parse_qs(self.rfile.read(int(self.headers['Content-Length'])).decode(), keep_blank_values=True)

        if 'config' not in form_data:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b"Missing config file")
            return

        try:
            config_json = json.loads(form_data['config'][0])
        except json.JSONDecodeError:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b"Invalid JSON")
            return

        is_valid, message = validate_json(config_json)
        if not is_valid:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(message.encode())
            return

        if 'legacy_xml' in config_json and not parse_safe_xml(config_json['legacy_xml']):
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b"Invalid XML")
            return

        if 'calc_expr' in config_json:
            is_valid, message = compile_expression(config_json['calc_expr'])
            if not is_valid:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(message.encode())
                return
            config_json['calc_expr'] = lambda x: eval(config_json['calc_expr'])

        serialized_config = serialize_config(config_json)
        if not serialized_config:
            self.send_response(500)
            self.end_headers()
            self.wfile.write(b"Failed to serialize config")
            return

        self.send_response(200)
        self.end_headers()
        self.wfile.write(serialized_config)

def run(server_class=HTTPServer, handler_class=ConfigHandler, port=8080):
    server_address = ('', port)
    httpd = server_class(server_address, handler_class)
    print(f'Starting httpd server on port {port}')
    httpd.serve_forever()

if __name__ == '__main__':
    run()