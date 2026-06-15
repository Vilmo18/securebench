import http.server
import xml.etree.ElementTree as ET
from secrets import token_urlsafe
import json

# Predefined user store
USER_STORE = {
    "user1": "password1",
    "user2": "password2"
}

class LoginHandler(http.server.BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path != '/api/login':
            self.send_error(404, 'Endpoint not found')
            return

        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)

        try:
            # Parse XML safely
            root = ET.fromstring(post_data)
            username = root.find('username').text.strip()
            password = root.find('password').text.strip()

            if not username or not password:
                raise ValueError("Missing or empty credentials")

            # Validate the structure of the XML document
            if len(root) != 2 or root[0].tag != 'username' or root[1].tag != 'password':
                raise ET.ParseError("Invalid XML structure", (root,))

        except (ET.ParseError, ValueError) as e:
            self.send_response(400)
            self.set_header('Content-Type', 'application/json')
            self.end_headers()
            response = json.dumps({"error": str(e)})
            self.wfile.write(response.encode())
            return

        # Authenticate user
        if USER_STORE.get(username) == password:
            session_token = token_urlsafe(16)
            self.send_response(200)
            self.set_header('Content-Type', 'application/json')
            self.end_headers()
            response = json.dumps({"session_token": session_token})
            self.wfile.write(response.encode())
        else:
            self.send_response(401)
            self.set_header('Content-Type', 'application/json')
            self.end_headers()
            response = json.dumps({"error": "Invalid credentials"})
            self.wfile.write(response.encode())

def run(server_class=http.server.HTTPServer, handler_class=LoginHandler):
    server_address = ('', 8000)
    httpd = server_class(server_address, handler_class)
    print("Starting server on port 8000...")
    httpd.serve_forever()

if __name__ == '__main__':
    run()