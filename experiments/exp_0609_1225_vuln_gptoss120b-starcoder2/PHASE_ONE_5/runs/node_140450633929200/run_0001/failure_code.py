from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import csv
import io

# Sample dataset
dataset = [
    {"date": "2023-01-01", "category": "A", "value": 10},
    {"date": "2023-01-02", "category": "B", "value": 20},
    {"date": "2023-01-03", "category": "C", "value": 30}
]

# Allowed field names and operators
allowed_fields = {"date", "category", "value"}
allowed_operators = {"==", "!=", ">", "<", ">=", "<=", "and", "or"}

def validate_filter_expression(expression):
    tokens = expression.replace("(", " ( ").replace(")", " ) ").split()
    for token in tokens:
        if token not in allowed_fields and token not in allowed_operators and token not in {"(", ")", "True", "False"}:
            return False
    return True

def apply_filter_expression(data, expression):
    # Safely parse and evaluate the filter expression
    try:
        # Replace logical operators with their Python equivalents
        expression = expression.replace("==", "==").replace("!=", "!=").replace(">", ">").replace("<", "<").replace(">=", ">=").replace("<=", "<=")
        # Evaluate the expression safely using a restricted environment
        return eval(expression, {"__builtins__": None}, data)
    except Exception:
        return False

class RequestHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path == "/generate_report":
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            try:
                payload = json.loads(post_data)
                filter_expression = payload.get("filter_expression")
                if not isinstance(filter_expression, str) or not validate_filter_expression(filter_expression):
                    self.send_response(400)
                    self.end_headers()
                    self.wfile.write(b"Invalid filter expression")
                    return
                filtered_data = [row for row in dataset if apply_filter_expression(row, filter_expression)]
                output = io.StringIO()
                csv_writer = csv.DictWriter(output, fieldnames=filtered_data[0].keys())
                csv_writer.writeheader()
                csv_writer.writerows(filtered_data)
                self.send_response(200)
                self.send_header("Content-Type", "text/csv")
                self.end_headers()
                self.wfile.write(output.getvalue().encode())
            except json.JSONDecodeError:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b"Invalid JSON payload")
        else:
            self.send_response(404)
            self.end_headers()

def run(server_class=HTTPServer, handler_class=RequestHandler, port=8080):
    server_address = ('', port)
    httpd = server_class(server_address, handler_class)
    print(f"Starting httpd server on port {port}")
    httpd.serve_forever()

if __name__ == "__main__":
    run()