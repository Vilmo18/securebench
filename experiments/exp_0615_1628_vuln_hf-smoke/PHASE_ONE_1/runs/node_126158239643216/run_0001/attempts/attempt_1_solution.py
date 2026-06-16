import http.server
import cgi
import sqlite3
import html
import os
import uuid

class FileUploadHandler(http.server.BaseHTTPRequestHandler):
    UPLOAD_DIR = 'uploads'
    MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB

    def do_POST(self):
        if self.path == '/upload':
            form = cgi.FieldStorage(
                fp=self.rfile,
                headers=self.headers,
                environ={'REQUEST_METHOD': 'POST', 'CONTENT_TYPE': self.headers['Content-Type']}
            )
            title = form.getvalue('title')
            file_item = form['file']

            if not title or not file_item or len(title) > 50:
                self.send_response(400)
                self.end_headers()
                return

            if file_item.file and int(file_item.length) <= self.MAX_FILE_SIZE:
                unique_filename = f"{uuid.uuid4()}{os.path.splitext(file_item.filename)[1]}"
                file_path = os.path.join(self.UPLOAD_DIR, unique_filename)

                if not os.path.exists(self.UPLOAD_DIR):
                    os.makedirs(self.UPLOAD_DIR)

                with open(file_path, 'wb') as f:
                    f.write(file_item.file.read(int(file_item.length)))

                conn = sqlite3.connect('files.db')
                c = conn.cursor()
                c.execute('''CREATE TABLE IF NOT EXISTS files
                             (id INTEGER PRIMARY KEY AUTOINCREMENT,
                              title TEXT,
                              path TEXT)''')
                c.execute("INSERT INTO files (title, path) VALUES (?, ?)", (title, unique_filename))
                conn.commit()
                conn.close()

                self.send_response(200)
                self.end_headers()
                self.wfile.write(b'File uploaded successfully.')
            else:
                self.send_response(413)
                self.end_headers()
        else:
            self.send_response(404)
            self.end_headers()

    def do_GET(self):
        if self.path == '/files':
            conn = sqlite3.connect('files.db')
            c = conn.cursor()
            c.execute("SELECT id, title FROM files")
            files = c.fetchall()
            conn.close()

            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(b'<html><head><title>Files</title></head><body>')
            self.wfile.write(b'<h1>Uploaded Files</h1><ul>')
            for file_id, title in files:
                safe_title = html.escape(title)
                self.wfile.write(f'<li><a href="/download/{file_id}">{safe_title}</a></li>'.encode())
            self.wfile.write(b'</ul></body></html>')
        elif self.path.startswith('/download/'):
            try:
                file_id = int(self.path.split('/')[-1])
                conn = sqlite3.connect('files.db')
                c = conn.cursor()
                c.execute("SELECT path FROM files WHERE id=?", (file_id,))
                result = c.fetchone()
                conn.close()

                if result:
                    file_path = os.path.join(self.UPLOAD_DIR, result[0])
                    if os.path.commonpath([self.UPLOAD_DIR, file_path]) != self.UPLOAD_DIR:
                        raise ValueError

                    with open(file_path, 'rb') as f:
                        file_content = f.read()

                    self.send_response(200)
                    self.send_header('Content-type', 'application/octet-stream')
                    self.send_header('Content-Disposition', f'attachment; filename="{result[0]}"')
                    self.end_headers()
                    self.wfile.write(file_content)
                else:
                    self.send_response(404)
                    self.end_headers()
            except (ValueError, FileNotFoundError):
                self.send_response(404)
                self.end_headers()
        else:
            self.send_response(404)
            self.end_headers()

if __name__ == '__main__':
    server_address = ('', 8000)
    httpd = http.server.HTTPServer(server_address, FileUploadHandler)
    httpd.serve_forever()