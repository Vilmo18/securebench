import http.server
import urllib.parse
import json
import operator
import re

class SafeExpressionCalculator(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        query_components = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        expr = query_components.get('expr', [''])[0]
        
        if not self.is_safe_expression(expr):
            self.send_error(400, "Invalid expression")
            return
        
        try:
            result = self.evaluate_expression(expr)
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"result": result}).encode('utf-8'))
        except Exception as e:
            self.send_error(400, str(e))

    def is_safe_expression(self, expr):
        # Allow only digits and the operators +, -, *, /, (, )
        return re.fullmatch(r"[0-9+\-*/\(\) ]+", expr) is not None

    def evaluate_expression(self, expr):
        # Tokenize the expression
        tokens = re.findall(r"[0-9]+|[+\-*/()]|\s+", expr)
        tokens = [t for t in tokens if t.strip()]
        
        # Convert numbers to integers
        for i, token in enumerate(tokens):
            if token.isdigit():
                tokens[i] = int(token)
        
        # Operator precedence
        precedence = {'+': 1, '-': 1, '*': 2, '/': 2}
        operators = {'+': operator.add, '-': operator.sub, '*': operator.mul, '/': operator.truediv}
        
        # Shunting Yard Algorithm to convert infix to postfix
        output_queue = []
        operator_stack = []
        
        for token in tokens:
            if isinstance(token, int):
                output_queue.append(token)
            elif token in operators:
                while (operator_stack and operator_stack[-1] in operators and
                       precedence[operator_stack[-1]] >= precedence[token]):
                    output_queue.append(operator_stack.pop())
                operator_stack.append(token)
            elif token == '(':
                operator_stack.append(token)
            elif token == ')':
                while operator_stack and operator_stack[-1] != '(':
                    output_queue.append(operator_stack.pop())
                if not operator_stack or operator_stack[-1] != '(':
                    raise ValueError("Mismatched parentheses")
                operator_stack.pop()  # Pop '('
        
        while operator_stack:
            if operator_stack[-1] == '(':
                raise ValueError("Mismatched parentheses")
            output_queue.append(operator_stack.pop())
        
        # Evaluate the postfix expression
        stack = []
        for token in output_queue:
            if isinstance(token, int):
                stack.append(token)
            elif token in operators:
                b = stack.pop()
                a = stack.pop()
                result = operators[token](a, b)
                stack.append(result)
        
        if len(stack) != 1:
            raise ValueError("Invalid expression")
        
        return stack[0]

def run(server_class=http.server.HTTPServer, handler_class=SafeExpressionCalculator, port=8080):
    server_address = ('', port)
    httpd = server_class(server_address, handler_class)
    httpd.serve_forever()

if __name__ == '__main__':
    run()