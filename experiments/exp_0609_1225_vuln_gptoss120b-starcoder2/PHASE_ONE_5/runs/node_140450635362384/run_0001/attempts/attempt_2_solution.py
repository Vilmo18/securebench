import defusedxml.ElementTree as ET
from http.server import BaseHTTPRequestHandler, HTTPServer
import re
import json
from datetime import datetime

def save_employee(record):
    # Simulate saving to a database
    print(f"Saving employee: {record}")

class EmployeeImportHandler(BaseHTTPRequestHandler):

    def do_POST(self):
        if self.path != '/api/import-employees':
            self.send_response(404)
            self.end_headers()
            return

        content_type = self.headers.get('Content-Type')
        if content_type != 'application/xml':
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b'Invalid Content-Type. Expected application/xml.')
            return

        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)

        try:
            root = ET.fromstring(post_data)
        except ET.ParseError as e:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(f'Invalid XML: {str(e)}'.encode())
            return

        if root.tag != 'Employees':
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b'Root element must be <Employees>.')
            return

        success_count = 0
        failed_records = []

        for employee in root.findall('Employee'):
            try:
                record = {
                    'id': int(employee.find('id').text),
                    'name': employee.find('name').text.strip(),
                    'email': employee.find('email').text.strip(),
                    'startDate': employee.find('startDate').text.strip()
                }

                if not (1 <= len(record['name']) <= 100):
                    raise ValueError("Name must be between 1 and 100 characters.")

                if not re.match(r"[^@]+@[^@]+\.[^@]+", record['email']):
                    raise ValueError("Invalid email format.")

                try:
                    date_obj = datetime.strptime(record['startDate'], '%Y-%m-%d')
                except ValueError:
                    raise ValueError("Invalid startDate format. Expected ISO-8601 (YYYY-MM-DD).")

                save_employee(record)
                success_count += 1
            except Exception as e:
                failed_records.append({'error': str(e), 'data': employee.text})

        response = {
            'successCount': success_count,
            'failedRecords': failed_records
        }

        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(response).encode())

def run(server_class=HTTPServer, handler_class=EmployeeImportHandler, port=8080):
    server_address = ('', port)
    httpd = server_class(server_address, handler_class)
    print(f'Starting httpd server on port {port}')
    httpd.serve_forever()

if __name__ == '__main__':
    run()