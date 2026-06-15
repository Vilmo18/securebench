import http.server
import sqlite3

class UserDeletionHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        # Validate the user ID parameter
        try:
            user_id = int(self.path.split('=')[1])
        except ValueError:
            self.send_error(400, 'Invalid user ID')
            return

        # Check if the requesting user has administrative privileges
        session = self.server.sessions[self.client_address]
        role = session['role']
        if role != 'admin':
            self.send_error(403, 'Forbidden')
            return

        # Perform the deletion
        with sqlite3.connect('users.db') as db:
            cursor = db.cursor()
            cursor.execute('DELETE FROM users WHERE id = ?', (user_id,))
            db.commit()

        # Return a JSON response indicating success or failure
        if cursor.rowcount == 1:
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'{"success": true}')
        else:
            self.send_error(404, 'User not found')

if __name__ == '__main__':
    http.server.HTTPServer(('localhost', 8000), UserDeletionHandler).serve_forever()