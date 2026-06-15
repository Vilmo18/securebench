import http.server
import sqlite3

class RecordAPI:
    def __init__(self):
        self.db = sqlite3.connect('records.db')
        self.cursor = self.db.cursor()

    def handle_request(self, request):
        if request.method == 'POST' and request.headers['Content-Type'] == 'application/json':
            try:
                data = request.get_json()
                user_id = int(data['user_id'])
                search = data['search'].strip().replace('%', '')[:200]
                if len(search) > 0 and all(c in printable for c in search):
                    self.cursor.execute("SELECT * FROM records WHERE user_id = ? AND data LIKE ?", (user_id, f'%{search}%'))
                    results = self.cursor.fetchall()
                    return http.server.Response(200, json.dumps(results).encode('utf-8'), [('Content-Type', 'application/json')])
                else:
                    return http.server.Response(400, b'Invalid input data')
            except (KeyError, ValueError, sqlite3.Error):
                return http.server.Response(400, b'Invalid input data')
        else:
            return http.server.Response(405, b'Method not allowed')

if __name__ == '__main__':
    RecordAPI().handle_request(http.server.Request('POST', '/api/records', {'Content-Type': 'application/json'}, b'{"user_id": 123, "search": "abc"}'))