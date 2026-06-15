import json
from http.server import BaseHTTPRequestHandler, HTTPServer

class UserProfileImportAPI(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path == '/api/v1/import_profiles':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            try:
                profiles = json.loads(post_data)
            except json.JSONDecodeError:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b'Invalid JSON')
                return

            if not isinstance(profiles, list):
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b'Profiles must be a list of objects')
                return

            valid_profiles = []
            for profile in profiles:
                if not all(key in profile for key in ['username', 'email', 'role']):
                    self.send_response(400)
                    self.end_headers()
                    self.wfile.write(b'Missing required fields: username, email, role')
                    return

                username = profile['username']
                email = profile['email']
                role = profile['role']

                if not isinstance(username, str) or not username:
                    self.send_response(400)
                    self.end_headers()
                    self.wfile.write(b'Invalid username')
                    return
                if not self.is_valid_email(email):
                    self.send_response(400)
                    self.end_headers()
                    self.wfile.write(b'Invalid email format')
                    return
                if role not in ['admin', 'user']:
                    self.send_response(400)
                    self.end_headers()
                    self.wfile.write(b'Role must be either admin or user')
                    return

                metadata = profile.get('metadata', {})
                if not isinstance(metadata, dict):
                    self.send_response(400)
                    self.end_headers()
                    self.wfile.write(b'Metadata must be a JSON object')
                    return
                for key, value in metadata.items():
                    if not isinstance(key, str) or not isinstance(value, (str, int, float, bool)):
                        self.send_response(400)
                        self.end_headers()
                        self.wfile.write(b'Invalid metadata format')
                        return

                valid_profiles.append({
                    'username': username,
                    'email': email,
                    'role': role,
                    'metadata': metadata
                })

            # Simulate database insertion (for demonstration purposes only)
            for profile in valid_profiles:
                print(f"Inserting into database: {profile}")

            self.send_response(200)
            self.end_headers()
            response = json.dumps({'imported_count': len(valid_profiles)})
            self.wfile.write(response.encode())
        else:
            self.send_response(404)
            self.end_headers()

    def is_valid_email(self, email):
        import re
        return bool(re.match(r"^[^@]+@[^@]+\.[^@]+$", email))

def run(server_class=HTTPServer, handler_class=UserProfileImportAPI, port=8080):
    server_address = ('', port)
    httpd = server_class(server_address, handler_class)
    print(f'Starting httpd server on port {port}')
    httpd.serve_forever()

if __name__ == '__main__':
    run()