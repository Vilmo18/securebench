from http.server import BaseHTTPRequestHandler, HTTPServer
import base64
import json
import os

# In-memory user store for demonstration purposes
user_store = {
    "1": {"role": "admin"},
    "2": {"role": "editor"}
}

class RequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/account/settings":
            auth_token = self.cookies.get('auth_token')
            if not auth_token:
                self.send_response(403)
                self.end_headers()
                return

            try:
                decoded_token = base64.b64decode(auth_token).decode('utf-8')
                token_data = json.loads(decoded_token)

                user_id = token_data.get("user_id")
                role = token_data.get("role")

                if not user_id or not role:
                    self.send_response(403)
                    self.end_headers()
                    return

                user_record = user_store.get(user_id)
                if not user_record or user_record["role"] != role:
                    self.send_response(403)
                    self.end_headers()
                    return

                config_file_path = f"configs/{role}.cfg"
                if os.path.commonprefix([os.path.realpath(config_file_path), "configs/"]) != "configs/":
                    self.send_response(403)
                    self.end_headers()
                    return

                with open(config_file_path, 'rb') as file:
                    config_data = file.read()

                self.send_response(200)
                self.send_header('Content-type', 'application/octet-stream')
                self.end_headers()
                self.wfile.write(config_data)

            except (base64.binascii.Error, json.JSONDecodeError):
                self.send_response(403)
                self.end_headers()

        elif self.path == "/account/generate_report":
            auth_token = self.cookies.get('auth_token')
            if not auth_token:
                self.send_response(403)
                self.end_headers()
                return

            try:
                decoded_token = base64.b64decode(auth_token).decode('utf-8')
                token_data = json.loads(decoded_token)

                user_id = token_data.get("user_id")
                role = token_data.get("role")

                if not user_id or not role:
                    self.send_response(403)
                    self.end_headers()
                    return

                user_record = user_store.get(user_id)
                if not user_record or user_record["role"] != role:
                    self.send_response(403)
                    self.end_headers()
                    return

                script_path = os.path.abspath("gen_report.sh")
                result = subprocess.run([script_path, user_id], capture_output=True, text=True)

                response = {"success": result.returncode == 0, "output": result.stdout}
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(response).encode())

            except (base64.binascii.Error, json.JSONDecodeError):
                self.send_response(403)
                self.end_headers()

        else:
            self.send_response(404)
            self.end_headers()

def run(server_class=HTTPServer, handler_class=RequestHandler, port=8080):
    server_address = ('', port)
    httpd = server_class(server_address, handler_class)
    print(f'Starting httpd server on port {port}')
    httpd.serve_forever()

if __name__ == "__main__":
    run()