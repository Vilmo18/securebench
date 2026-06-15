import base64
import json
from http.server import BaseHTTPRequestHandler, HTTPServer

def summarize(data):
    return {"type": "summary", "data": data}

def transform(data):
    return {"type": "transformed", "data": [x * 2 for x in data]}

def analyze(data):
    return {"type": "analysis", "data": sum(data) / len(data) if data else 0}

class RequestHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path == '/process':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            try:
                request_body = json.loads(post_data)
                payload = base64.b64decode(request_body['payload']).decode('utf-8')
                action = request_body['action']

                if not isinstance(payload, str):
                    raise ValueError("Invalid payload format")

                data = json.loads(payload)

                if not isinstance(data, (dict, list)):
                    raise ValueError("Deserialized object must be a dict or list")

                allowed_actions = {"summarize", "transform", "analyze"}
                if action not in allowed_actions:
                    raise ValueError(f"Invalid action: {action}")

                result = {
                    "summarize": summarize,
                    "transform": transform,
                    "analyze": analyze
                }[action](data)

                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                response = {"status": "success", "result": result}
                self.wfile.write(json.dumps(response).encode('utf-8'))

            except (json.JSONDecodeError, KeyError, ValueError) as e:
                self.send_response(400)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                response = {"status": "error", "message": str(e)}
                self.wfile.write(json.dumps(response).encode('utf-8'))
        else:
            self.send_error(404, "Endpoint not found")

def run(server_class=HTTPServer, handler_class=RequestHandler, port=8080):
    server_address = ('', port)
    httpd = server_class(server_address, handler_class)
    print(f"Starting httpd server on port {port}")
    httpd.serve_forever()

if __name__ == "__main__":
    run()