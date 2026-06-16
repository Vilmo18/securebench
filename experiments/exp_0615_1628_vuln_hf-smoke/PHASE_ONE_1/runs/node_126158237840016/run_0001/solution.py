import http.server
import json
import re

class UserProfileUpdateHandler(http.server.BaseHTTPRequestHandler):
    def do_POST(self):
        if not self.path.startswith('/api/users/'):
            self.send_error(404, 'Not Found')
            return

        try:
            user_id_from_path = self.path.split('/')[3]
        except IndexError:
            self.send_error(400, 'Invalid user ID in URL')
            return

        auth_header = self.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            self.send_error(401, 'Unauthorized')
            return

        jwt_token = auth_header.split(' ')[1]
        try:
            user_id_from_token = self.decode_jwt(jwt_token)
        except ValueError:
            self.send_error(401, 'Invalid JWT token')
            return

        if user_id_from_path != user_id_from_token:
            self.send_error(403, 'Forbidden')
            return

        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length)
        try:
            data = json.loads(post_data)
        except json.JSONDecodeError:
            self.send_error(400, 'Invalid JSON payload')
            return

        email = data.get('email')
        age = data.get('age')

        errors = []
        if not isinstance(email, str) or not re.match(r'^(?:[a-zA-Z0-9!#$%&amp;\'*+/=?^_`{|}~-]+(?:\.[a-zA-Z0-9!#$%&amp;\'*+/=?^_`{|}~-]+)*|"(?:[\x01-\x08\x0b\x0c\x0e-\x1f\x21\x23-\x5b\x5d-\x7f]|\\[\x01-\x09\x0b\x0c\x0e-\x7f])*")@(?:(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]*[a-zA-Z0-9])?\.)+[a-zA-Z0-9](?:[a-zA-Z0-9-]*[a-zA-Z0-9])?$', email):
            errors.append('Invalid email format')
        if not isinstance(age, int) or not (13 <= age <= 120):
            errors.append('Age must be an integer between 13 and 120')

        if errors:
            self.send_response(400)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'errors': errors}).encode())
            return

        # Simulate updating the user profile in the data store
        self.update_user_profile(user_id_from_path, email, age)

        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({'message': 'Profile updated successfully'}).encode())

    def decode_jwt(self, token):
        # This is a simplified placeholder for JWT decoding logic
        # In a real-world scenario, use a secure library like PyJWT
        parts = token.split('.')
        if len(parts) != 3:
            raise ValueError('Invalid JWT token format')
        payload = parts[1]
        import base64
        decoded_payload = base64.urlsafe_b64decode(payload + '==').decode()
        claims = json.loads(decoded_payload)
        return claims.get('user_id')

    def update_user_profile(self, user_id, email, age):
        # Placeholder function to simulate updating user profile
        pass

def run(server_class=http.server.HTTPServer, handler_class=UserProfileUpdateHandler, port=8080):
    server_address = ('', port)
    httpd = server_class(server_address, handler_class)
    httpd.serve_forever()

if __name__ == '__main__':
    run()