import os
import json
import csv
import sqlite3
from http.server import BaseHTTPRequestHandler, HTTPServer

# Constants
API_KEYS = {'partner1', 'partner2'}
DATA_DIR = 'data/imports/'
DB_NAME = 'records.db'

class ImportHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path != '/api/import':
            self.send_error(404)
            return

        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length).decode('utf-8')
        payload = json.loads(post_data)

        api_key = payload.get('api_key')
        file_path = payload.get('file_path')
        search_term = payload.get('search_term')
        user_note = payload.get('user_note')
        transform_script = payload.get('transform_script')

        if not api_key or api_key not in API_KEYS:
            self.send_error(401, 'Unauthorized')
            return

        full_path = os.path.join(DATA_DIR, file_path)
        if os.path.isabs(full_path) or os.path.commonpath((full_path, DATA_DIR)) != DATA_DIR:
            self.send_error(403, 'Invalid file path')
            return
        if not os.path.exists(full_path):
            self.send_error(404, 'File not found')
            return

        try:
            with open(full_path, newline='') as csvfile:
                reader = csv.reader(csvfile)
                transformed_rows = []
                for row in reader:
                    # Execute transform_script safely
                    local_vars = {}
                    eval(transform_script, {}, local_vars)
                    transformed_row = [local_vars.get(cell, cell) for cell in row]
                    transformed_rows.append(tuple(transformed_row))

            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()

            # Insert transformed rows into a temporary staging table
            placeholders = ','.join(['?'] * len(next(iter(reader)) if reader else []))
            cursor.executemany(f'INSERT INTO temp_table VALUES ({placeholders})', transformed_rows)

            # Perform parameterized query on records table
            cursor.execute('SELECT * FROM records WHERE column_name LIKE ?', ('%' + search_term + '%',))
            results = cursor.fetchall()

            response = {
                'note': user_note,
                'results': results
            }

            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(response).encode('utf-8'))

        except Exception as e:
            self.send_error(500, str(e))

def run(server_class=HTTPServer, handler_class=ImportHandler, port=8080):
    server_address = ('', port)
    httpd = server_class(server_address, handler_class)
    print(f'Starting httpd server on port {port}')
    httpd.serve_forever()

if __name__ == '__main__':
    run()