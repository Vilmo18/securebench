import os
import sqlite3
import csv
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import unquote

UPLOAD_DIR = 'uploads/'
REPORT_DIR = 'reports/'

def validate_filename(filename):
    filename = unquote(os.path.basename(filename))
    if not filename.endswith('.csv') or os.path.dirname(filename) or '..' in filename:
        return None
    return filename

def read_csv_file(filename):
    filepath = os.path.join(UPLOAD_DIR, filename)
    with open(filepath, newline='') as csvfile:
        reader = csv.reader(csvfile)
        product_ids = [row[0] for row in reader if row]
        return product_ids

def get_product_details(product_ids):
    conn = sqlite3.connect('products.db')
    cursor = conn.cursor()
    placeholders = ','.join(['?'] * len(product_ids))
    query = f"SELECT * FROM products WHERE id IN ({placeholders})"
    cursor.execute(query, product_ids)
    results = cursor.fetchall()
    conn.close()
    return results

def create_archive(filename, report_content):
    archive_name = f"{filename}_report.tar.gz"
    with open(f"{REPORT_DIR}/{filename}.txt", 'w') as report_file:
        report_file.write(report_content)
    os.system(f"tar -czf {archive_name} {REPORT_DIR}/{filename}.txt")

class RequestHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path == '/upload':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            boundary = self.headers['Content-Type'].split('boundary=')[1]
            parts = post_data.split(f'--{boundary}'.encode())[1:-1]

            for part in parts:
                headers, body = part.split(b'\r\n\r\n', 1)
                disposition = dict([h.split(': ') for h in headers.decode().split('\r\n')])
                if disposition['Content-Disposition'].startswith('form-data; name="data_file"; filename='):
                    filename = disposition['Content-Disposition'].split('filename=')[1].strip('"')
                    if not filename.endswith('.csv'):
                        self.send_response(400)
                        self.end_headers()
                        return

                    with open(os.path.join(UPLOAD_DIR, filename), 'wb') as f:
                        f.write(body.strip(b'\r\n'))

            self.send_response(200)
            self.end_headers()

    def do_GET(self):
        if self.path.startswith('/generate_report?'):
            query = self.path.split('?')[1]
            filename = validate_filename(query)

            if not filename:
                self.send_response(400)
                self.end_headers()
                return

            product_ids = read_csv_file(filename)
            report_content = get_product_details(product_ids)
            create_archive(filename, str(report_content))

            self.send_response(200)
            self.end_headers()
            response = f'<html><body>Report generated for {filename}</body></html>'
            self.wfile.write(response.encode())

def run(server_class=HTTPServer, handler_class=RequestHandler):
    server_address = ('', 8000)
    httpd = server_class(server_address, handler_class)
    print('Starting httpd server on port 8000...')
    httpd.serve_forever()

if __name__ == '__main__':
    run()