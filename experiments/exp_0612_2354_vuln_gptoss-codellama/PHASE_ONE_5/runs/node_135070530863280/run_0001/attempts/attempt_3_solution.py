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
            request_data = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
        except json.JSONDecodeError:
            self.send_error(400, 'Invalid JSON payload')
            return

        # Validate input data
        if not request_data or 'query' not in request_data or 'params' not in request_data:
            self.send_error(400, 'Missing query or params in request data')
            return

        # Prepare SQL query and parameters
        sql = request_data['query']
        params = tuple(request_data['params'])

        # Execute SQL query with safe parameters
        try:
            cursor = sqlite3.connect(DB_PATH).cursor()
            cursor.execute(sql, params)
            results = cursor.fetchall()
            cursor.close()
        except Exception as e:
            self.send_error(500, 'Error executing SQL query')
            return

        # Return results
        self.send_response(200)
        self.end_headers()
        self.wfile.write(json.dumps(results).encode('utf-8'))

if __name__ == "__main__":
    http.server.test(RequestHandlerClass=RequestHandler, port=8000)