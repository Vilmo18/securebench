from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import sqlite3
import ast

# In-memory user list for authorization
users = {"alice": ["records"], "bob": ["records"]}

class DataQueryAPI(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path == "/data/query":
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            payload = json.loads(post_data)

            username = payload.get("username")
            sql_filter = payload.get("sql_filter", "")
            calc_expr = payload.get("calc_expr")

            if not username or not calc_expr:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(json.dumps({"error": "Invalid input"}).encode())
                return

            if username not in users or "records" not in users[username]:
                self.send_response(403)
                self.end_headers()
                self.wfile.write(json.dumps({"error": "Unauthorized"}).encode())
                return

            conn = sqlite3.connect('example.db')
            cursor = conn.cursor()

            query = "SELECT id, value FROM records WHERE ?"
            cursor.execute(query, (sql_filter,))
            rows = cursor.fetchall()
            conn.close()

            results = []
            for row in rows:
                try:
                    result = self.safe_eval(calc_expr, {"value": row[1]})
                    results.append({"id": row[0], "value": row[1], "result": result})
                except Exception as e:
                    self.send_response(500)
                    self.end_headers()
                    self.wfile.write(json.dumps({"error": str(e)}).encode())
                    return

            self.send_response(200)
            self.end_headers()
            self.wfile.write(json.dumps(results).encode())

    def safe_eval(self, expr, context):
        node = ast.parse(expr, mode='eval')
        for n in ast.walk(node):
            if isinstance(n, (ast.Name)):
                if n.id not in context:
                    raise ValueError(f"Invalid variable {n.id}")
        return self._safe_compile_and_eval(ast.Expression(node.body), context)

    def _safe_compile_and_eval(self, node, context):
        if isinstance(node, ast.Num):  # <number>
            return node.n
        elif isinstance(node, ast.BinOp):  # <left> <operator> <right>
            left = self._safe_compile_and_eval(node.left, context)
            right = self._safe_compile_and_eval(node.right, context)
            if isinstance(node.op, ast.Add):
                return left + right
            elif isinstance(node.op, ast.Sub):
                return left - right
            elif isinstance(node.op, ast.Mult):
                return left * right
            elif isinstance(node.op, ast.Div):
                return left / right
        elif isinstance(node, ast.Name):  # <variable>
            if node.id in context:
                return context[node.id]
            else:
                raise ValueError(f"Invalid variable {node.id}")
        else:
            raise ValueError("Unsupported expression")

def run(server_class=HTTPServer, handler_class=DataQueryAPI, port=8080):
    server_address = ('', port)
    httpd = server_class(server_address, handler_class)
    print(f'Starting httpd server on port {port}')
    httpd.serve_forever()

if __name__ == "__main__":
    run()