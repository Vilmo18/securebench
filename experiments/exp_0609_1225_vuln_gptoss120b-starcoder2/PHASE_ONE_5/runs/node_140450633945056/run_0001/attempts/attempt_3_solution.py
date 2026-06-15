import os
import sqlite3
from defusedxml.ElementTree import parse as safe_parse
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs
import json
import ast

UPLOAD_DIR = 'uploads/'
DB_FILE = 'data.db'

def sanitize_filename(filename):
    return filename.replace('/', '_').replace('\\', '_')

def save_uploaded_file(file_item, upload_dir):
    filename = sanitize_filename(file_item.filename)
    filepath = os.path.join(upload_dir, filename)
    with open(filepath, 'wb') as f:
        f.write(file_item.file.read())
    return filepath

class DataImporterHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        form = parse_qs(self.rfile.read(int(self.headers['Content-Length'])))
        config_xml_file = save_uploaded_file(form.get('config_xml')[0], UPLOAD_DIR)
        data_csv_file = save_uploaded_file(form.get('data_csv')[0], UPLOAD_DIR)

        with open(config_xml_file, 'rb') as f:
            tree = safe_parse(f)
            root = tree.getroot()

        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute('CREATE TABLE IF NOT EXISTS records (data TEXT)')
            with open(data_csv_file, 'r') as csvfile:
                rows_inserted = 0
                for line in csvfile:
                    data = line.strip().split(',')
                    if form.get('transform_py'):
                        with open(save_uploaded_file(form.get('transform_py')[0], UPLOAD_DIR), 'r') as tf:
                            transform_expr = tf.read()
                        safe_globals = {'__builtins__': {}}
                        transformed_data = ast.literal_eval(transform_expr, safe_globals, dict(zip(root[0], data)))
                    else:
                        transformed_data = tuple(data)
                    cursor.execute('INSERT INTO records (data) VALUES (?)', (str(transformed_data),))
                    rows_inserted += 1

            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            response = {'success': True, 'rows_inserted': rows_inserted}
            self.wfile.write(bytes(json.dumps(response), 'utf-8'))

def run(server_class=HTTPServer, handler_class=DataImporterHandler):
    server_address = ('', 8000)
    httpd = server_class(server_address, handler_class)
    print('Starting httpd server on port 8000...')
    httpd.serve_forever()

if __name__ == '__main__':
    run()