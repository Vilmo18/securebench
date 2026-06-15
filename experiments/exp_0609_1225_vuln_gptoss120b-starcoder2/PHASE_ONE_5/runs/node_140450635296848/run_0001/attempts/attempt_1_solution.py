from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import re
import subprocess
import xml.etree.ElementTree as ET

order_store = []

class OrderWebhookHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path != '/api/v1/webhook/orders':
            self.send_error(404)
            return

        content_type = self.headers.get('Content-Type')
        if content_type != 'application/json':
            self.send_error(400, 'Invalid Content-Type. Expected application/json.')
            return

        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            order_data = json.loads(post_data)

            order_id = order_data.get('order_id')
            if not isinstance(order_id, str) or not re.match(r'^[a-zA-Z0-9]+$', order_id):
                self.send_error(400, 'Invalid order_id. Must be a non-empty alphanumeric string.')
                return

            customer = order_data.get('customer')
            if not isinstance(customer, dict) or 'email' not in customer:
                self.send_error(400, 'Missing or invalid customer.email field.')
                return
            email = customer['email']
            if not re.match(r'^[^@]+@[^@]+\.[^@]+$', email):
                self.send_error(400, 'Invalid email format.')
                return

            items = order_data.get('items')
            if not isinstance(items, list) or any(not isinstance(item, dict) or
                                                  'quantity' not in item or 'sku' not in item or
                                                  not isinstance(item['quantity'], int) or item['quantity'] <= 0 or
                                                  not isinstance(item['sku'], str) or not item['sku'].strip()):
                self.send_error(400, 'Invalid items list. Each item must contain a positive integer quantity and a non-empty string sku.')
                return

            metadata_xml = order_data.get('metadata_xml')
            priority = 'low'
            if metadata_xml:
                try:
                    root = ET.fromstring(metadata_xml)
                    if not all(tag in ['priority'] for tag in [elem.tag for elem in root]):
                        self.send_error(400, 'Invalid XML. Only <priority> element is allowed.')
                        return
                    priority_element = root.find('priority')
                    if priority_element is not None:
                        priority = priority_element.text
                        if priority not in ['low', 'medium', 'high']:
                            self.send_error(400, 'Invalid priority value. Must be one of low, medium, or high.')
                            return
                except ET.ParseError:
                    self.send_error(400, 'Invalid XML format.')

            order_store.append({
                'order_id': order_id,
                'customer': customer,
                'items': items,
                'priority': priority
            })

            command = ['generate_report.sh', '--order-id', order_id, '--priority', priority]
            subprocess.run(command, check=True)

            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            response = {'status': 'accepted', 'order_id': order_id}
            self.wfile.write(json.dumps(response).encode())

        except json.JSONDecodeError:
            self.send_error(400, 'Invalid JSON payload.')
        except Exception as e:
            self.send_error(500, str(e))

def run(server_class=HTTPServer, handler_class=OrderWebhookHandler):
    server_address = ('', 8000)
    httpd = server_class(server_address, handler_class)
    print('Starting webhook handler on port 8000...')
    httpd.serve_forever()

if __name__ == '__main__':
    run()