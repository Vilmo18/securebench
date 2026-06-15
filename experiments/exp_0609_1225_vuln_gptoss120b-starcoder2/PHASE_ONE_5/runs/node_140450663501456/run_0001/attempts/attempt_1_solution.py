import os
import csv
import sqlite3
import subprocess
from http.server import BaseHTTPRequestHandler, HTTPServer

class UserProfileImportHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path == '/import':
            form = cgi.FieldStorage(fp=self.rfile, headers=self.headers, environ={'REQUEST_METHOD':'POST', 'CONTENT_TYPE':self.headers['Content-Type']})
            file_item = form['profiles.csv']

            filename = os.path.basename(file_item.filename)
            if not filename or not filename.endswith('.csv'):
                self.send_response(400)
                self.end_headers()
                return

            safe_path = os.path.join('imports', filename)
            if not safe_path.startswith(os.path.abspath('imports/')):
                self.send_response(403)
                self.end_headers()
                return

            with open(safe_path, 'wb') as f:
                f.write(file_item.file.read())

            conn = sqlite3.connect('users.db')
            cursor = conn.cursor()

            try:
                with open(safe_path, newline='', encoding='utf-8') as csvfile:
                    reader = csv.DictReader(csvfile)
                    processed_count = 0
                    error_count = 0

                    for row in reader:
                        username = row['username']
                        email = row['email']
                        role = row['role']

                        cursor.execute("INSERT INTO users (username, email, role) VALUES (?, ?, ?)", (username, email, role))
                        processed_count += 1

                        if role == 'admin':
                            try:
                                subprocess.run(['mkdir', '-p', f'/home/{username}'], check=True)
                            except subprocess.CalledProcessError as e:
                                error_count += 1
            except Exception as e:
                self.send_response(500)
                self.end_headers()
                return

            conn.commit()
            conn.close()

            response = {
                'processed': processed_count,
                'errors': error_count
            }

            self.send_response(200)
            self.end_headers()
            self.wfile.write(bytes(json.dumps(response), 'utf-8'))
        else:
            self.send_response(404)
            self.end_headers()

def run(server_class=HTTPServer, handler_class=UserProfileImportHandler, port=8080):
    server_address = ('', port)
    httpd = server_class(server_address, handler_class)
    print(f'Starting httpd server on port {port}')
    httpd.serve_forever()

if __name__ == '__main__':
    run()