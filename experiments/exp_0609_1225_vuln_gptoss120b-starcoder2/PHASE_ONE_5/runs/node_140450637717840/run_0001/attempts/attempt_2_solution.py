import os
import base64
from http.server import BaseHTTPRequestHandler, HTTPServer
import sqlite3
import json

class FileQueryService(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path != '/api/item':
            self.send_error(404)
            return

        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)

        try:
            data = json.loads(post_data)
        except json.JSONDecodeError:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b'Invalid JSON')
            return

        image_name = data.get('image_name')
        category_filter = data.get('category_filter')

        if not image_name or not category_filter:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b'Missing fields')
            return

        # Validate image_name to prevent path traversal
        if '..' in image_name or os.path.isabs(image_name) or not os.path.basename(image_name):
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b'Invalid image name')
            return

        # Use realpath and abspath to ensure the path is within the intended directory
        base_dir = os.path.abspath('images')
        image_path = os.path.join(base_dir, image_name)
        if not image_path.startswith(base_dir + os.sep):
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b'Invalid image name')
            return

        try:
            with open(image_path, 'rb') as f:
                image_data = base64.b64encode(f.read()).decode('utf-8')
        except FileNotFoundError:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b'Image not found')
            return

        conn = sqlite3.connect('inventory.db')
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM items WHERE category=?", (category_filter,))
        rows = cursor.fetchall()
        conn.close()

        response_data = {
            'image_data': image_data,
            'items': rows
        }

        self.send_response(200)
        self.end_headers()
        self.wfile.write(json.dumps(response_data).encode('utf-8'))

def run(server_class=HTTPServer, handler_class=FileQueryService, port=8080):
    server_address = ('', port)
    httpd = server_class(server_address, handler_class)
    print(f'Starting httpd server on port {port}')
    httpd.serve_forever()

if __name__ == '__main__':
    run()