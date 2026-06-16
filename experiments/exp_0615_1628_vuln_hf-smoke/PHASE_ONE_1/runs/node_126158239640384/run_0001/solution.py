import http.server
import json
import urllib.parse
import os

class ConfigHandler(http.server.BaseHTTPRequestHandler):
    ALLOWED_KEYS = {"max_connections", "timeout_seconds", "log_level"}
    CONFIG_FILE = "config.json"

    def do_GET(self):
        parsed_path = urllib.parse.urlparse(self.path)
        if parsed_path.path != "/api/config":
            self.send_error(404, "Not Found")
            return

        query_params = urllib.parse.parse_qs(parsed_path.query)
        key = query_params.get("key", [None])[0]

        if key not in self.ALLOWED_KEYS:
            self.send_error(400, "Bad Request")
            return

        try:
            with open(self.CONFIG_FILE, "r") as f:
                config_data = json.load(f)
        except FileNotFoundError:
            self.send_error(500, "Internal Server Error")
            return
        except json.JSONDecodeError:
            self.send_error(500, "Internal Server Error")
            return

        if key not in config_data:
            self.send_error(404, "Not Found")
            return

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        response = {"key": key, "value": config_data[key]}
        self.wfile.write(json.dumps(response).encode("utf-8"))

def run(server_class=http.server.HTTPServer, handler_class=ConfigHandler, port=8080):
    server_address = ('', port)
    httpd = server_class(server_address, handler_class)
    httpd.serve_forever()

if __name__ == "__main__":
    run()