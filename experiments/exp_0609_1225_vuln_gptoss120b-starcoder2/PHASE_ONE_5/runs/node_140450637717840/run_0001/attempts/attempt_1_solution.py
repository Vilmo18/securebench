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

        if '..' in image_name or os.path.isabs(image_name):
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b'Invalid image name')
            return

        image_path = os.path.join('images', image_name)

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