import json
import logging
import operator
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs

# Configure logging
logging.basicConfig(filename='evaluation.log', level=logging.INFO, format='%(asctime)s - %(message)s')

# Define allowed operators
operators = {
    '+': operator.add,
    '-': operator.sub,
    '*': operator.mul,
    '/': operator.truediv
}

def evaluate_expression(expr):
    # Tokenize the expression
    tokens = expr.replace(' ', '').split('+')
    stack = []
    
    for token in tokens:
        sub_tokens = token.split('-')
        if len(sub_tokens) > 1:
            stack.append(float(sub_tokens[0]))
            for sub_token in sub_tokens[1:]:
                stack.append(-float(sub_token))
        else:
            stack.append(float(sub_tokens[0]))
    
    result = stack[0]
    i = 1
    while i < len(stack):
        op = expr[i]
        if op in operators:
            result = operators[op](result, stack[i+1])
            i += 2
        else:
            raise ValueError("Invalid operator")
    
    return result

class EvaluateHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        
        try:
            data = json.loads(post_data)
            expr = data.get('expr', '')
            
            if not expr:
                raise ValueError("Expression is missing")
            
            # Validate expression
            valid_chars = set('0123456789+-*/(). ')
            if not all(c in valid_chars for c in expr):
                raise ValueError("Invalid characters in expression")
            
            # Evaluate expression
            result = evaluate_expression(expr)
            
            # Log the request and result safely
            logging.info(f"Expression: {expr!r}, Result: {result}")
            
            # Send response
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            response = json.dumps({'result': result})
            self.wfile.write(response.encode('utf-8'))
        
        except Exception as e:
            # Log the error
            logging.error(f"Error evaluating expression: {str(e)}")
            
            # Send error response
            self.send_response(400)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            response = json.dumps({'error': str(e)})
            self.wfile.write(response.encode('utf-8'))

def run(server_class=HTTPServer, handler_class=EvaluateHandler, port=8080):
    server_address = ('', port)
    httpd = server_class(server_address, handler_class)
    logging.info(f'Starting httpd on port {port}...')
    httpd.serve_forever()

if __name__ == '__main__':
    run()