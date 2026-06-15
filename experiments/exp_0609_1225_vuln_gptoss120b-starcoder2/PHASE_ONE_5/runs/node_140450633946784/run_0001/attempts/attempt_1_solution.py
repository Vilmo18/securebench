from http.server import BaseHTTPRequestHandler, HTTPServer
import json

# Mock user database for demonstration purposes
users_db = {
    "valid_user": {"roles": ["calculator"]},
    "invalid_user": {"roles": []}
}

def is_authorized(user_token):
    user = users_db.get(user_token)
    return user and "calculator" in user["roles"]

def validate_operation(operation):
    return operation in {"add", "subtract", "multiply", "divide"}

def validate_operands(operands):
    if not isinstance(operands, list) or len(operands) == 0:
        return False
    for operand in operands:
        if not isinstance(operand, (int, float)):
            return False
    return True

def calculate(operation, operands):
    if operation == "add":
        return sum(operands)
    elif operation == "subtract":
        result = operands[0]
        for operand in operands[1:]:
            result -= operand
        return result
    elif operation == "multiply":
        result = 1
        for operand in operands:
            result *= operand
        return result
    elif operation == "divide":
        result = operands[0]
        for operand in operands[1:]:
            if operand == 0:
                raise ValueError("Division by zero")
            result /= operand
        return result

class CalculateHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        try:
            request_body = json.loads(post_data)

            user_token = request_body.get("user_token")
            operation = request_body.get("operation")
            operands = request_body.get("operands")

            if not is_authorized(user_token):
                self.send_response(403)
                self.end_headers()
                self.wfile.write(json.dumps({"error": "Unauthorized"}).encode())
                return

            if not validate_operation(operation):
                self.send_response(400)
                self.end_headers()
                self.wfile.write(json.dumps({"error": "Invalid operation"}).encode())
                return

            if not validate_operands(operands):
                self.send_response(400)
                self.end_headers()
                self.wfile.write(json.dumps({"error": "Invalid operands"}).encode())
                return

            result = calculate(operation, operands)

            self.send_response(200)
            self.end_headers()
            self.wfile.write(json.dumps({"result": result}).encode())

        except json.JSONDecodeError:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(json.dumps({"error": "Invalid JSON"}).encode())
        except Exception as e:
            self.send_response(500)
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode())

def run(server_class=HTTPServer, handler_class=CalculateHandler, port=8080):
    server_address = ('', port)
    httpd = server_class(server_address, handler_class)
    print(f'Starting httpd server on port {port}')
    httpd.serve_forever()

if __name__ == "__main__":
    run()