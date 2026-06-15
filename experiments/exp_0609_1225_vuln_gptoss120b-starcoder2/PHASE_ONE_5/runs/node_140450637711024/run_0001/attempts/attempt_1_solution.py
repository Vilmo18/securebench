import os
import sqlite3
import csv
from http.server import BaseHTTPRequestHandler, HTTPServer

# Mock session storage for CSRF token validation (in a real app, this would be part of the session management)
session_storage = {
    "user1": {"role": "admin", "csrf_token": "valid_csrf_token"},
}

class ExportProfileHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path != '/export_profile':
            self.send_error(404, 'Endpoint not found')
            return

        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        import json
        request_body = json.loads(post_data)

        employee_id = request_body.get('employee_id')
        export_format = request_body.get('export_format')
        csrf_token = request_body.get('csrf_token')

        # Validate input
        if not isinstance(employee_id, str) or not employee_id.isdigit() or not employee_id:
            self.send_error(400, 'Invalid employee ID')
            return

        if export_format != "csv":
            self.send_error(400, 'Unsupported export format')
            return

        # Mock user session (in a real app, this would be retrieved from the session)
        current_user = "user1"

        # CSRF token validation
        expected_csrf_token = session_storage[current_user]["csrf_token"]
        if csrf_token != expected_csrf_token:
            self.send_error(403, 'Invalid CSRF token')
            return

        # Authorization check (simplified for this example)
        user_role = session_storage[current_user]["role"]
        if user_role != "admin":
            self.send_error(403, 'Unauthorized to export profile')
            return

        # Database query
        conn = sqlite3.connect('employees.db')  # Replace with actual DB connection logic
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM employees WHERE id=?", (employee_id,))
        employee_data = cursor.fetchone()

        if not employee_data:
            self.send_error(404, 'Employee not found')
            return

        # Generate CSV file
        exports_dir = "exports"
        os.makedirs(exports_dir, exist_ok=True)
        csv_file_path = os.path.join(exports_dir, f"profile_{employee_id}.csv")

        with open(csv_file_path, mode='w', newline='') as csv_file:
            writer = csv.writer(csv_file)
            writer.writerow(["ID", "Name", "Position"])  # Example headers
            writer.writerow(employee_data)

        # Send file response
        self.send_response(200)
        self.send_header('Content-Type', 'text/csv')
        self.send_header('Content-Disposition', f'attachment; filename=profile_{employee_id}.csv')
        self.end_headers()

        with open(csv_file_path, 'rb') as file:
            self.wfile.write(file.read())

        # Clean up the temporary CSV file
        os.remove(csv_file_path)

def run(server_class=HTTPServer, handler_class=ExportProfileHandler, port=8080):
    server_address = ('', port)
    httpd = server_class(server_address, handler_class)
    print(f'Starting httpd server on port {port}')
    httpd.serve_forever()

if __name__ == '__main__':
    run()