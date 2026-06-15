import json
import psycopg2
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse

DB_CONFIG = {
    'dbname': 'your_db_name',
    'user': 'your_db_user',
    'password': 'your_db_password',
    'host': 'your_db_host',
    'port': 'your_db_port'
}

def escape_html(text):
    return text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;').replace("'", '&#39;')

class SyncProfileHandler(BaseHTTPRequestHandler):

    def do_POST(self):
        if self.path != '/api/sync_profile':
            self.send_error(404)
            return

        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)

        try:
            payload = json.loads(post_data)
        except json.JSONDecodeError:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(json.dumps({'error': 'Invalid JSON'}).encode())
            return

        user_id = payload.get('user_id')
        display_name = payload.get('display_name')
        bio = payload.get('bio')

        if not isinstance(user_id, int) or user_id <= 0:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(json.dumps({'error': 'Invalid user_id'}).encode())
            return

        if not (isinstance(display_name, str) and len(display_name) <= 150):
            self.send_response(400)
            self.end_headers()
            self.wfile.write(json.dumps({'error': 'Invalid display_name'}).encode())
            return

        if not (isinstance(bio, str) and len(bio) <= 150):
            self.send_response(400)
            self.end_headers()
            self.wfile.write(json.dumps({'error': 'Invalid bio'}).encode())
            return

        display_name = escape_html(display_name)
        bio = escape_html(bio)

        try:
            connection = psycopg2.connect(**DB_CONFIG)
            cursor = connection.cursor()

            query = """
                INSERT INTO users (id, display_name, bio) VALUES (%s, %s, %s)
                ON CONFLICT (id) DO UPDATE SET
                display_name = EXCLUDED.display_name,
                bio = EXCLUDED.bio;
            """

            cursor.execute(query, (user_id, display_name, bio))
            connection.commit()

        except psycopg2.Error as e:
            self.send_response(500)
            self.end_headers()
            self.wfile.write(json.dumps({'error': str(e)}).encode())
            return
        finally:
            cursor.close()
            connection.close()

        self.send_response(200)
        self.end_headers()
        response = {'status': 'ok', 'user_id': user_id}
        self.wfile.write(json.dumps(response).encode())

def run(server_class=HTTPServer, handler_class=SyncProfileHandler):
    parser = urlparse('http://localhost:8080')
    server_address = (parser.hostname, parser.port)
    httpd = server_class(server_address, handler_class)
    print(f'Starting httpd server on {server_address[0]}:{server_address[1]}')
    httpd.serve_forever()

if __name__ == '__main__':
    run()