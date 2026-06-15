import sqlite3
import base64
from xml.etree.ElementTree import fromstring, ParseError
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs
import html

# Mock database setup (in-memory for this example)
def setup_database():
    conn = sqlite3.connect(':memory:')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE products (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL
        )
    ''')
    cursor.execute('''
        CREATE TABLE profiles (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL
        )
    ''')
    cursor.executemany('INSERT INTO products (name) VALUES (?)', [('Product 1',), ('Product 2',)])
    cursor.executemany('INSERT INTO profiles (name) VALUES (?)', [('Profile 1',), ('Profile 2',)])
    conn.commit()
    return conn

class DashboardHandler(BaseHTTPRequestHandler):
    def do_get(self):
        parsed_path = urlparse(self.path)
        query_params = parse_qs(parsed_path.query)

        search = query_params.get('search', [''])[0]
        profile_id_str = query_params.get('profile_id', [None])[0]
        xml_data = query_params.get('xml_data', [None])[0]

        if not profile_id_str or not profile_id_str.isdigit():
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b'Invalid profile_id')
            return

        profile_id = int(profile_id_str)

        conn = setup_database()
        cursor = conn.cursor()

        # Fetch profile
        cursor.execute('SELECT name FROM profiles WHERE id = ?', (profile_id,))
        profile_row = cursor.fetchone()
        if not profile_row:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b'Profile not found')
            return

        profile_name = html.escape(profile_row[0])

        # Fetch products
        search_param = '%' + search + '%'
        cursor.execute('SELECT name FROM products WHERE name LIKE ?', (search_param,))
        product_rows = cursor.fetchall()

        # Parse XML data if provided
        message_text = ''
        if xml_data:
            try:
                xml_bytes = base64.b64decode(xml_data)
                xml_str = xml_bytes.decode('utf-8')
                root = fromstring(xml_str)
                message_elem = root.find('message')
                if message_elem is not None:
                    message_text = html.escape(message_elem.text or '')
            except (base64.binascii.Error, ParseError):
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b'Invalid xml_data')
                return

        # Generate HTML response
        self.send_response(200)
        self.end_headers()

        html_content = f'''
        <html>
            <head><title>Dashboard</title></head>
            <body>
                <h1>Welcome, {profile_name}</h1>
                <table border="1">
                    <tr><th>Product Name</th></tr>
        '''

        for product_row in product_rows:
            product_name = html.escape(product_row[0])
            html_content += f'<tr><td>{product_name}</td></tr>'

        html_content += '</table>'

        if message_text:
            html_content += f'<div class="banner">{message_text}</div>'

        html_content += '</body></html>'
        self.wfile.write(html_content.encode('utf-8'))

def run(server_class=HTTPServer, handler_class=DashboardHandler):
    server_address = ('', 8000)
    httpd = server_class(server_address, handler_class)
    print('Starting httpd server on port 8000...')
    httpd.serve_forever()

if __name__ == '__main__':
    run()