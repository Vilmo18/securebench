import http.server
import sqlite3
import os
import html
import secrets

class SecureFileManagementSystem(http.server.BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path == '/upload':
            self.handle_upload()
        elif self.path == '/delete':
            self.handle_delete()
        else:
            self.send_response(404)
            self.end_headers()

    def handle_upload(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        boundary = self.headers['Content-Type'].split('=')[1].encode()
        parts = post_data.split(boundary)

        filename = None
        description = ''
        file_content = None

        for part in parts:
            lines = part.splitlines()
            for line in lines:
                if b'filename=' in line:
                    filename = line.decode().split('filename=')[1].strip('"')
                elif b'name="description"' in line:
                    description = lines[lines.index(line) + 2].decode()
                elif b'name="file"' in line:
                    file_content = lines[lines.index(line) + 2]

        if not filename or any(char in filename for char in ('/', '\\', '\0')):
            self.send_response(400)
            self.end_headers()
            return

        unique_storage_name = f"{secrets.token_hex(8)}_{os.path.basename(filename)}"
        file_path = os.path.join('files', unique_storage_name)

        # Ensure the file path is within the designated directory
        if not os.path.commonpath([os.path.abspath('files'), os.path.abspath(file_path)]) == os.path.abspath('files'):
            self.send_response(400)
            self.end_headers()
            return

        with open(file_path, 'wb') as f:
            f.write(file_content)

        conn = sqlite3.connect('files.db')
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS files
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      original_name TEXT NOT NULL,
                      description TEXT,
                      path TEXT NOT NULL)''')
        c.execute("INSERT INTO files (original_name, description, path) VALUES (?, ?, ?)",
                  (filename, description, file_path))
        conn.commit()
        file_id = c.lastrowid
        conn.close()

        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(f"File uploaded successfully with ID: {file_id}".encode())

    def handle_delete(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        post_data = post_data.decode().split('&')
        file_id = None
        csrf_token = None

        for item in post_data:
            key, value = item.split('=')
            if key == 'file_id':
                file_id = value
            elif key == 'csrf_token':
                csrf_token = value

        if not file_id or not csrf_token:
            self.send_response(400)
            self.end_headers()
            return

        session_csrf_token = self.get_session_csrf_token()
        if csrf_token != session_csrf_token:
            self.send_response(403)
            self.end_headers()
            return

        conn = sqlite3.connect('files.db')
        c = conn.cursor()
        c.execute("SELECT path FROM files WHERE id=?", (file_id,))
        row = c.fetchone()
        conn.close()

        if not row:
            self.send_response(404)
            self.end_headers()
            return

        file_path = row[0]
        if not file_path.startswith(os.path.abspath('files') + os.sep):
            self.send_response(400)
            self.end_headers()
            return

        # Ensure the file path is within the designated directory
        if not os.path.commonpath([os.path.abspath('files'), os.path.abspath(file_path)]) == os.path.abspath('files'):
            self.send_response(400)
            self.end_headers()
            return

        try:
            os.remove(file_path)
        except FileNotFoundError:
            self.send_response(404)
            self.end_headers()
            return

        conn = sqlite3.connect('files.db')
        c = conn.cursor()
        c.execute("DELETE FROM files WHERE id=?", (file_id,))
        conn.commit()
        conn.close()

        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(b"File deleted successfully")

    def do_GET(self):
        if self.path == '/list':
            self.handle_list()
        else:
            self.send_response(404)
            self.end_headers()

    def handle_list(self):
        conn = sqlite3.connect('files.db')
        c = conn.cursor()
        c.execute("SELECT original_name, description, id FROM files")
        rows = c.fetchall()
        conn.close()

        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()

        csrf_token = self.get_session_csrf_token()
        html_content = "<html><body><h1>Files</h1><ul>"
        for row in rows:
            original_name = html.escape(row[0])
            description = html.escape(row[1])
            file_id = row[2]
            html_content += f"<li>{original_name} - {description} <a href='/delete?file_id={file_id}&csrf_token={csrf_token}'>Delete</a></li>"
        html_content += "</ul></body></html>"

        self.wfile.write(html_content.encode())

    def get_session_csrf_token(self):
        if 'csrf_token' not in self.server.session:
            self.server.session['csrf_token'] = secrets.token_urlsafe(16)
        return self.server.session['csrf_token']

def run(server_class=http.server.HTTPServer, handler_class=SecureFileManagementSystem, port=8080):
    server_address = ('', port)
    httpd = server_class(server_address, handler_class)
    httpd.session = {}
    print(f'Starting httpd on port {port}...')
    httpd.serve_forever()

if __name__ == '__main__':
    run()