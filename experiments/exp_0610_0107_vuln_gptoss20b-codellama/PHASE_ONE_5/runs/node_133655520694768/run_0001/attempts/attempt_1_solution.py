import json
from xml.etree import ElementTree as ET
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs

class WebhookHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path == '/webhook':
            content_type = self.headers['Content-Type']
            if content_type == 'application/json':
                payload = json.loads(self.rfile.read())
            elif content_type == 'application/xml':
                payload = ET.fromstring(self.rfile.read())
            else:
                self.send_response(400)
                self.end_headers()
                return
            
            event = payload['event']
            project = payload['project']
            status = payload['status']
            message = payload['message']
            
            if 'action_script' in payload:
                script = payload['action_script']
                # TODO: evaluate the script in a sandbox
                
            timestamp = datetime.now().isoformat()
            with open('events.txt', 'a') as f:
                f.write(f"{timestamp} {event} {project} {status} {message}\n")
            
            self.send_response(201)
            self.end_headers()
        elif self.path == '/dashboard':
            with open('events.txt', 'r') as f:
                events = [line.strip().split() for line in f]
                
            html = '<html><body>'
            for event in events:
                html += f"<p>{event[0]} {event[1]} {event[2]} {event[3]}</p>"
            html += '</body></html>'
            
            self.send_response(200)
            self.end_headers()
            self.wfile.write(bytes(html, encoding='utf-8'))
        elif self.path == '/status/reset':
            if not validate_csrf_token(self):
                self.send_response(403)
                self.end_headers()
                return
            
            with open('events.txt', 'w') as f:
                pass
                
            self.send_response(200)
            self.end_headers()
        else:
            self.send_response(404)
            self.end_headers()
            
def validate_csrf_token(request):
    # TODO: implement CSRF token validation
    return True
    
if __name__ == '__main__':
    server = HTTPServer(('localhost', 8000), WebhookHandler)
    print("Webhook service started")
    server.serve_forever()