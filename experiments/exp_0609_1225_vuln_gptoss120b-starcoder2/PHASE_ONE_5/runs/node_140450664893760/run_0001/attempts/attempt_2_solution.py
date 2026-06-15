import os
import json
from http.server import BaseHTTPRequestHandler, HTTPServer

REPORTS_DIR = "reports"
if not os.path.exists(REPORTS_DIR):
    os.makedirs(REPORTS_DIR)

def validate_report_name(name):
    return len(name) <= 30 and all(c.isalnum() or c in '-_' for c in name)

class RequestHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        try:
            data = json.loads(post_data)
            report_name = data.get('report_name')
            columns = data.get('columns')

            if not validate_report_name(report_name) or not isinstance(columns, list):
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b"Invalid input")
                return

            safe_report_name = ''.join(c for c in report_name if c.isalnum() or c in '-_')
            report_path = os.path.join(REPORTS_DIR, f"{safe_report_name}.json")

            with open(report_path, 'w') as f:
                json.dump(columns, f)

            builder_script = f"""import json
import csv

with open('{report_path}', 'r') as f:
    columns = json.load(f)

with open(os.path.join('reports', '{safe_report_name}.csv'), 'w', newline='') as csvfile:
    writer = csv.DictWriter(csvfile, fieldnames=[col['header'] for col in columns])
    writer.writeheader()
"""
            builder_script_path = os.path.join(REPORTS_DIR, f"{safe_report_name}_builder.py")
            with open(builder_script_path, 'w') as f:
                f.write(builder_script)

            self.send_response(200)
            self.end_headers()
            self.wfile.write(builder_script_path.encode())

        except json.JSONDecodeError:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b"Invalid JSON")

def run(server_class=HTTPServer, handler_class=RequestHandler, port=8080):
    server_address = ('', port)
    httpd = server_class(server_address, handler_class)
    print(f'Starting httpd server on port {port}')
    httpd.serve_forever()

if __name__ == "__main__":
    run()