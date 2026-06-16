import re
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from subprocess import run, PIPE, CalledProcessError

ALLOWED_EXPRESSION_NODES = {'Num', 'BinOp', 'Add', 'Sub', 'Mult', 'Div', 'Call', 'Name', 'Load'}
WHITELISTED_COMMANDS = {"echo", "date", "whoami"}

def is_safe_expression(node):
    if node._fields:
        return all(is_safe_expression(getattr(node, field)) for field in node._fields)
    return type(node).__name__ in ALLOWED_EXPRESSION_NODES

def validate_expression(expression):
    try:
        import ast
        tree = ast.parse(expression, mode='eval')
        return all(is_safe_expression(n) for n in ast.walk(tree))
    except SyntaxError:
        return False

def validate_command(command):
    if not command:
        return False
    parts = command.split()
    if parts[0] not in WHITELISTED_COMMANDS:
        return False
    for part in parts[1:]:
        if re.search(r'[;&|<>]', part):
            return False
    return True

class RequestHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        try:
            data = json.loads(post_data)
            expression = data.get('expression')
            command = data.get('command')
            
            if not expression or not command:
                raise ValueError("Missing 'expression' or 'command' in request")
            
            if not validate_expression(expression):
                raise ValueError("Invalid expression")
            
            if not validate_command(command):
                raise ValueError("Invalid command")
            
            result = eval(expression, {"__builtins__": None}, {"abs": abs, "round": round})
            if not isinstance(result, (int, float)):
                raise ValueError("Expression did not evaluate to a number")
            
            cmd_parts = command.split()
            output = run(cmd_parts, check=True, stdout=PIPE, stderr=PIPE).stdout.decode().strip()
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"result": result, "output": output}).encode())
        
        except (ValueError, CalledProcessError) as e:
            self.send_response(400)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode())

def run_server(port=8080):
    server_address = ('', port)
    httpd = HTTPServer(server_address, RequestHandler)
    httpd.serve_forever()

if __name__ == '__main__':
    run_server()