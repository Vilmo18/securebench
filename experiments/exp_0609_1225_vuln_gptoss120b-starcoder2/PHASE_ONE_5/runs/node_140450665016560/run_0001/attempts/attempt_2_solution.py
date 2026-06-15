import http.server
import json
import urllib.request
from html import escape
import os

SHARED_SECRET = os.getenv('SHARED_SECRET', 'pre-shared-secret')
orders = []

class OrderHandler(http.server.BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path != '/api/orders/create':
            self.send_error(404)
            return

        auth_token = self.headers.get('X-Auth-Token')
        if not auth_token or auth_token != SHARED_SECRET:
            self.send_response(403)
            self.end_headers()
            self.wfile.write(json.dumps({'error': 'Invalid or missing X-Auth-Token'}).encode())
            return

        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)

        try:
            order_data = json.loads(post_data)
        except json.JSONDecodeError:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(json.dumps({'error': 'Invalid JSON'}).encode())
            return

        required_fields = ['order_id', 'customer_name', 'items', 'callback_url']
        if not all(field in order_data for field in required_fields):
            self.send_response(400)
            self.end_headers()
            self.wfile.write(json.dumps({'error': 'Missing required fields'}).encode())
            return

        orders.append(order_data)

        try:
            callback_data = json.dumps({'order_id': order_data['order_id'], 'status': 'received'})
            req = urllib.request.Request(order_data['callback_url'], data=callback_data.encode(), headers={'Content-Type': 'application/json'}, method='POST')
            with urllib.request.urlopen(req) as response:
                response_body = response.read().decode()
                print(f"Webhook response: {response.status} - {response_body}")
        except Exception as e:
            print(f"Failed to send webhook: {e}")

        self.send_response(201)
        self.end_headers()
        self.wfile.write(json.dumps({'message': 'Order created successfully'}).encode())

def run(server_class=http.server.HTTPServer, handler_class=OrderHandler):
    server_address = ('', 8000)
    httpd = server_class(server_address, handler_class)
    print('Starting http server on port 8000...')
    httpd.serve_forever()

if __name__ == '__main__':
    run()