import os
import json
import re
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse
from ast import parse, NodeVisitor, Expression, Import, ImportFrom, FunctionDef, ClassDef

# Predefined dataset for demonstration purposes
records = [
    {"id": 1, "name": "Alice", "department": "HR"},
    {"id": 2, "name": "Bob", "department": "Engineering"},
    {"id": 3, "name": "Charlie", "department": "Marketing"}
]

# Allowed built-ins for safe evaluation
ALLOWED_BUILTINS = {
    'abs': abs,
    'all': all,
    'any': any,
    'ascii': ascii,
    'bin': bin,
    'bool': bool,
    'bytearray': bytearray,
    'bytes': bytes,
    'chr': chr,
    'complex': complex,
    'dict': dict,
    'divmod': divmod,
    'enumerate': enumerate,
    'filter': filter,
    'float': float,
    'format': format,
    'frozenset': frozenset,
    'getattr': getattr,
    'hasattr': hasattr,
    'hash': hash,
    'hex': hex,
    'int': int,
    'isinstance': isinstance,
    'issubclass': issubclass,
    'iter': iter,
    'len': len,
    'list': list,
    'map': map,
    'max': max,
    'min': min,
    'next': next,
    'object': object,
    'oct': oct,
    'ord': ord,
    'pow': pow,
    'range': range,
    'repr': repr,
    'reversed': reversed,
    'round': round,
    'set': set,
    'slice': slice,
    'sorted': sorted,
    'str': str,
    'sum': sum,
    'tuple': tuple,
    'type': type,
    'zip': zip
}

# Dummy authentication function for demonstration purposes
def authenticate(token):
    # This should be replaced with actual token validation logic
    if token == "valid_admin_token":
        return {"role": "admin"}
    elif token == "valid_user_token":
        return {"role": "user"}
    return None

class SafeEvalVisitor(NodeVisitor):
    def visit_Import(self, node):
        raise ValueError("Import statements are not allowed")
    
    def visit_ImportFrom(self, node):
        raise ValueError("Import statements are not allowed")
    
    def visit_FunctionDef(self, node):
        raise ValueError("Function definitions are not allowed")
    
    def visit_ClassDef(self, node):
        raise ValueError("Class definitions are not allowed")

class AdminReportHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path != '/admin/report':
            self.send_error(404, "Not Found")
            return
        
        auth_header = self.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            self.send_error(403, "Forbidden")
            return
        
        token = auth_header.split(' ')[1]
        user_info = authenticate(token)
        if not user_info or user_info.get('role') != 'admin':
            self.send_error(403, "Forbidden")
            return
        
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        
        try:
            data = json.loads(post_data)
        except json.JSONDecodeError:
            self.send_error(400, "Bad Request: Invalid JSON")
            return
        
        filename = data.get('filename')
        filter_expr = data.get('filter_expr')
        
        if not isinstance(filename, str) or not filename:
            self.send_error(400, "Bad Request: Filename must be a non-empty string")
            return
        
        if not re.match(r'^[a-zA-Z0-9._-]+$', filename):
            self.send_error(400, "Bad Request: Filename contains invalid characters")
            return
        
        if filename.startswith('/') or '..' in filename or '\x00' in filename:
            self.send_error(400, "Bad Request: Invalid filename path")
            return
        
        full_path = os.path.join('reports', filename)
        if not full_path.startswith(os.path.abspath('reports')):
            self.send_error(400, "Bad Request: Attempted directory traversal")
            return
        
        if not isinstance(filter_expr, str) or not filter_expr:
            self.send_error(400, "Bad Request: Filter expression must be a non-empty string")
            return
        
        try:
            tree = parse(filter_expr, mode='eval')
            SafeEvalVisitor().visit(tree)
            compiled_expr = compile(tree, filename="<ast>", mode="eval")
            filtered_records = eval(compiled_expr, {"__builtins__": None}, {"records": records})
        except SyntaxError:
            self.send_error(400, "Bad Request: Syntax error in filter expression")
            return
        except ValueError as e:
            self.send_error(400, f"Bad Request: {e}")
            return
        except Exception as e:
            self.send_error(500, f"Internal Server Error: {e}")
            return
        
        if not isinstance(filtered_records, list):
            self.send_error(400, "Bad Request: Filter expression did not return a list")
            return
        
        try:
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, 'w') as f:
                json.dump(filtered_records, f)
        except IOError as e:
            self.send_error(500, f"Internal Server Error: Failed to write report file ({e})")
            return
        
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        response = {"status": "success"}
        self.wfile.write(json.dumps(response).encode('utf-8'))

def run(server_class=HTTPServer, handler_class=AdminReportHandler, port=8080):
    server_address = ('', port)
    httpd = server_class(server_address, handler_class)
    httpd.serve_forever()

if __name__ == '__main__':
    run()