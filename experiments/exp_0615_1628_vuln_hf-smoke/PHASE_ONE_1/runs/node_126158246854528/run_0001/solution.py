import http.server
import json

# In-memory data store for users
users = {
    1: {"role": "user"},
    2: {"role": "moderator"},
    3: {"role": "admin"}
}

def get_session_user():
    # This is a mock implementation of get_session_user
    # In a real scenario, this would extract user_id and role from the session cookie
    return (3, "admin")  # Example: returning an admin user

class RequestHandler(http.server.BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path != '/update_role':
            self.send_error(404, "Not Found")
            return

        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        
        try:
            payload = json.loads(post_data)
        except json.JSONDecodeError:
            self.send_error(400, "Invalid JSON")
            return

        target_user_id = payload.get('target_user_id')
        new_role = payload.get('new_role')

        if target_user_id is None or new_role is None or not isinstance(target_user_id, int) or new_role not in ["user", "moderator", "admin"]:
            self.send_error(400, "Missing or invalid fields")
            return

        requester_user_id, requester_role = get_session_user()

        if requester_role != "admin":
            self.send_response(403)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"error": "Forbidden"}).encode())
            return

        if target_user_id not in users:
            self.send_error(404, "User not found")
            return

        users[target_user_id]['role'] = new_role

        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({"message": "Role updated successfully"}).encode())

if __name__ == '__main__':
    server_address = ('', 8000)
    httpd = http.server.HTTPServer(server_address, RequestHandler)
    httpd.serve_forever()