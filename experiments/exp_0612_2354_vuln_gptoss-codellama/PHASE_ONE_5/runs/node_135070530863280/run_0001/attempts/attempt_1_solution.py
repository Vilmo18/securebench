import http.server
import json
import sqlite3

# Pre-populated SQLite database and user map
DB_PATH = 'data.db'
USERS = {
    'user1': 'password1',
    'user2': 'password2',
}

class RequestHandler(http.server.SimpleHTTPRequestHandler):
    def do_POST(self):
        # Authenticate user
        auth_token = self.headers.get('Authorization')
        if not auth_token or auth_token not in USERS:
            self.send_error(403, 'Invalid authentication token')
            return

        # Parse JSON payload
        try:
            data = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
        except (ValueError, KeyError):
            self.send_error(400, 'Invalid JSON payload')
            return

        # Validate query parameters
        table = data.get('table')
        if not table or table not in ['users', 'products']:
            self.send_error(400, 'Invalid table name')
            return

        columns = [c for c in data['query_params'].keys() if c != 'table']
        for col in columns:
            if col not in ['id', 'name', 'price'] or len(data['query_params'][col]) > 64:
                self.send_error(400, f'Invalid column name or value length: {col}')
                return

        # Construct and execute SQL query
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        sql = 'SELECT * FROM {} WHERE '.format(table) + ' AND '.join(['{} = ?'.format(c) for c in columns])
        params = [data['query_params'][col] for col in columns]
        try:
            cursor.execute(sql, params)
        except sqlite3.Error as e:
            self.send_error(400, f'SQLite error: {e}')
            return

        # Evaluate post script if provided
        post_script = data.get('post_script')
        if post_script:
            if len(post_script) > 128 or any(c in post_script for c in '{}()'):
                self.send_error(400, f'Invalid post script length or characters: {post_script}')
                return
            try:
                eval('lambda row: {}'.format(post_script), {'row': None}, {'len': len, 'int': int, 'float': float, 'str': str})
            except SyntaxError as e:
                self.send_error(400, f'Invalid post script syntax: {e}')
                return

        # Return JSON response
        rows = cursor.fetchall()
        if post_script:
            results = [{'script_result': eval('lambda row: {}'.format(post_script), {'row': r}, {'len': len, 'int': int, 'float': float, 'str': str})} for r in rows]
        else:
            results = [{c: v for c, v in zip(cursor.description, row)} for row in rows]
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(bytes(json.dumps(results), 'utf-8'))
        conn.close()

# Logging and error handling
def log_request(handler):
    user = handler.headers.get('Authorization') or '<anonymous>'
    table = handler.path[len('/api/run'):].split('?')[0]
    rows = len(json.loads(handler.rfile.read(int(handler.headers['Content-Length']))))
    print(f'{user} requested {table} with {rows} rows')

http.server.test(RequestHandlerClass=RequestHandler, bind_and_serve=('localhost', 8000), log_request=log_request)