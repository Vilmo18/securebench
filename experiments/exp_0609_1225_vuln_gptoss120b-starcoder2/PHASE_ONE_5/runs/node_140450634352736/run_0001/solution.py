import json
import os
import sqlite3
from http.server import BaseHTTPRequestHandler, HTTPServer

DB_PATH = 'customers.db'
TEMPLATE_DIR = 'templates/'

def validate_role(role):
    return role in {'viewer', 'admin'}

def sanitize_notes(notes):
    # Basic HTML escaping to prevent XSS
    escape_map = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#39;'
    }
    return ''.join(escape_map.get(c, c) for c in notes)

def validate_template_path(template_path, is_admin):
    if not is_admin:
        return False
    template_path = os.path.abspath(template_path)
    if not template_path.startswith(TEMPLATE_DIR):
        return False
    try:
        resolved_path = os.path.realpath(template_path)
        if not resolved_path.startswith(os.path.realpath(TEMPLATE_DIR)):
            return False
    except Exception:
        return False
    return True

def get_imported_records(sql_filter):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    query = "SELECT COUNT(*) FROM customers WHERE ?"
    cursor.execute(query, (sql_filter,))
    count = cursor.fetchone()[0]
    conn.close()
    return count

class ImportHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        try:
            data = json.loads(post_data)
            requester_role = data.get('requester_role')
            sql_filter = data.get('sql_filter')
            notes = data.get('notes', '')
            template_path = data.get('template_path')

            if not validate_role(requester_role):
                self.send_response(403, "Invalid role")
                return

            if requester_role == 'viewer' and template_path:
                self.send_response(403, "Viewer cannot specify a custom template path")
                return

            if template_path and not validate_template_path(template_path, requester_role == 'admin'):
                self.send_response(403, "Invalid template path")
                return

            notes = sanitize_notes(notes)
            imported_records_count = get_imported_records(sql_filter)

            response_data = {
                'status': 'success',
                'imported_records_count': imported_records_count,
                'notes': notes
            }

            self.send_response(200, "OK")
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(response_data).encode())

        except json.JSONDecodeError:
            self.send_response(400, "Invalid JSON")
        except Exception as e:
            self.send_response(500, str(e))

def run(server_class=HTTPServer, handler_class=ImportHandler, port=8080):
    server_address = ('', port)
    httpd = server_class(server_address, handler_class)
    print(f'Starting httpd server on port {port}')
    httpd.serve_forever()

if __name__ == '__main__':
    run()