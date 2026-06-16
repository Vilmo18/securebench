import re
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from subprocess import run, PIPE, CalledProcessError
import ast
import operator

ALLOWED_EXPRESSION_NODES = {'Num', 'BinOp', 'Add', 'Sub', 'Mult', 'Div', 'Call', 'Name', 'Load'}
WHITELISTED_COMMANDS = {"echo", "date", "whoami"}
OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
}

def is_safe_expression(node):
    if isinstance(node, ast.Num):
        return True
    elif isinstance(node, ast.BinOp):
        return (isinstance(node.op, tuple(OPERATORS.keys())) and
                is_safe_expression(node.left) and
                is_safe_expression(node.right))
    elif isinstance(node, ast.Call):
        return (isinstance(node.func, ast.Name) and
                node.func.id in {'abs', 'round'} and
                all(is_safe_expression(arg) for arg in node.args))
    elif isinstance(node, ast.Name):
        return node.id in {'abs', 'round'}
    elif isinstance(node, ast.Load):
        return True
    return False

def evaluate_expression(expression):
    try:
        tree = ast.parse(expression, mode='eval')
        if not all(is_safe_expression(n) for n in ast.walk(tree)):
            raise ValueError("Invalid expression")
        return _eval(tree.body)
    except SyntaxError:
        raise ValueError("Invalid expression")

def _eval(node):
    if isinstance(node, ast.Num):
        return node.n
    elif isinstance(node, ast.BinOp):
        left = _eval(node.left)
        right = _eval(node.right)
        return OPERATORS[type(node.op)](left, right)
    elif isinstance(node, ast.Call):
        func = eval(node.func.id, {"__builtins__": None}, {"abs": abs, "round": round})
        args = [_eval(arg) for arg in node.args]
        return func(*args)
    else:
        raise ValueError("Invalid expression")

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
            
            result = evaluate_expression(expression)
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