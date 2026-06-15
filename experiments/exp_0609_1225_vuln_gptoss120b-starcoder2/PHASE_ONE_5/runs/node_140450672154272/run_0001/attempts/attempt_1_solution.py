import base64
import json
import os
from http.server import BaseHTTPRequestHandler, HTTPServer

class PreferencesHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path != '/preferences':
            self.send_error(404)
            return

        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)

        try:
            payload = json.loads(post_data)
            settings_blob = payload.get('settings_blob')
            if not settings_blob:
                raise ValueError("Missing 'settings_blob' in request")

            decoded_bytes = base64.b64decode(settings_blob)
            user_prefs = json.loads(decoded_bytes)

            if not isinstance(user_prefs, dict) or \
               not all(k in user_prefs for k in ('theme', 'notifications', 'language')):
                raise ValueError("Invalid data structure")

            theme = user_prefs['theme']
            notifications = user_prefs['notifications']
            language = user_prefs['language']

            if theme not in ("light", "dark"):
                raise ValueError("Invalid value for 'theme'")
            if not isinstance(notifications, bool):
                raise ValueError("Invalid type for 'notifications'")
            if len(language) != 2 or not language.isalpha():
                raise ValueError("Invalid ISO-639-1 code for 'language'")

        except (json.JSONDecodeError, base64.binascii.Error, ValueError) as e:
            self.send_response(400)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            response = {'error': str(e)}
            self.wfile.write(json.dumps(response).encode())
            return

        user_id = "user123"  # Replace with actual authenticated user ID
        os.makedirs("user_prefs", exist_ok=True)
        file_path = f"user_prefs/{user_id}.json"

        try:
            with open(file_path, 'w') as pref_file:
                json.dump(user_prefs, pref_file)

            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            response = {'status': 'saved'}
            self.wfile.write(json.dumps(response).encode())
        except IOError as e:
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            response = {'error': str(e)}
            self.wfile.write(json.dumps(response).encode())

def run(server_class=HTTPServer, handler_class=PreferencesHandler):
    server_address = ('', 8000)
    httpd = server_class(server_address, handler_class)
    print("Starting httpd server on port 8000...")
    httpd.serve_forever()

if __name__ == "__main__":
    run()