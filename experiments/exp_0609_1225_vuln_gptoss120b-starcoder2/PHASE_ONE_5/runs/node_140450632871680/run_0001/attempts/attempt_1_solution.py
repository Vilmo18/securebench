import os
import sqlite3
from http.server import BaseHTTPRequestHandler, HTTPServer
import json

IMPORT_DIR = "/path/to/import/dir"
DATABASE_PATH = "customers.db"

class ImportAPI(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path != '/api/import':
            self.send_error(404)
            return

        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length).decode('utf-8')
            payload = json.loads(post_data)

            source_file = payload.get('source_file')
            sql_filter = payload.get('sql_filter')
            notes = payload.get('notes')

            if not all([source_file, sql_filter, notes]):
                self.send_error(400, "Missing required fields")
                return

            file_path = os.path.join(IMPORT_DIR, source_file)
            if not file_path.startswith(IMPORT_DIR) or not os.path.isfile(file_path):
                self.send_error(400, "Invalid source file")

            with open(file_path, 'r') as f:
                csv_data = f.read()

            conn = sqlite3.connect(DATABASE_PATH)
            cursor = conn.cursor()
            query = f"SELECT * FROM customers WHERE {sql_filter}"
            cursor.execute(query)
            rows = cursor.fetchall()
            conn.close()

            html_snippet = self.generate_html(rows, notes)

            self.send_response(200)
            self.send_header('Content-Type', 'text/html')
            self.end_headers()
            self.wfile.write(html_snippet.encode('utf-8'))

        except json.JSONDecodeError:
            self.send_error(400, "Invalid JSON")
        except Exception as e:
            self.send_error(500, str(e))

    def generate_html(self, rows, notes):
        html = f"<html><body><p>{notes}</p><table border='1'>"
        for row in rows:
            html += "<tr>"
            for cell in row:
                html += f"<td>{cell}</td>"
            html += "</tr>"
        html += "</table></body></html>"
        return html

def run(server_class=HTTPServer, handler_class=ImportAPI, port=8080):
    server_address = ('', port)
    httpd = server_class(server_address, handler_class)
    print(f"Starting httpd server on port {port}")
    httpd.serve_forever()

if __name__ == '__main__':
    run()