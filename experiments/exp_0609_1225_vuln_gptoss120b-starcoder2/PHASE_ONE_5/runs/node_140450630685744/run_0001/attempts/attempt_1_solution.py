import os
import sqlite3
import subprocess
import xml.etree.ElementTree as ET
from http.server import BaseHTTPRequestHandler, HTTPServer

CONFIG_DIR = 'configs/'
REPORT_DIR = 'reports/'
DB_PATH = 'internal.db'

def sanitize_filename(filename):
    return filename.replace('/', '_').replace('\\', '_').replace('..', '_')

def parse_xml(xml_content):
    tree = ET.ElementTree(ET.fromstring(xml_content))
    root = tree.getroot()
    sql_query = root.find('sql').text.strip() if root.find('sql') is not None else None
    command = root.find('command').text.strip() if root.find('command') is not None else None
    return sql_query, command

def execute_query(query):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(query)
    results = cursor.fetchall()
    conn.close()
    return results

class RequestHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path != '/upload':
            self.send_response(404)
            self.end_headers()
            return

        content_length = int(self.headers['Content-Length'])
        xml_content = self.rfile.read(content_length)

        try:
            sql_query, command = parse_xml(xml_content)
            if not sql_query or not sql_query.strip().lower().startswith('select'):
                raise ValueError("Invalid SQL query")

            config_filename = sanitize_filename('config.xml')
            with open(os.path.join(CONFIG_DIR, config_filename), 'w') as f:
                f.write(xml_content)

            results = execute_query(sql_query)
            report_filename = sanitize_filename(config_filename) + '.csv'
            with open(os.path.join(REPORT_DIR, report_filename), 'w') as f:
                for row in results:
                    f.write(','.join(map(str, row)) + '\n')

            if command:
                subprocess.run(['sh', '-c', command.replace('"', '\\"').replace("'", "\\'")], check=True)

            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            response = {'status': 'success', 'report_path': os.path.join(REPORT_DIR, report_filename)}
            self.wfile.write(bytes(json.dumps(response), 'utf-8'))

        except Exception as e:
            self.send_response(400)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            response = {'status': 'error', 'message': str(e)}
            self.wfile.write(bytes(json.dumps(response), 'utf-8'))

def run(server_class=HTTPServer, handler_class=RequestHandler):
    server_address = ('', 8000)
    httpd = server_class(server_address, handler_class)
    print('Starting httpd server on port 8000...')
    httpd.serve_forever()

if __name__ == '__main__':
    run()