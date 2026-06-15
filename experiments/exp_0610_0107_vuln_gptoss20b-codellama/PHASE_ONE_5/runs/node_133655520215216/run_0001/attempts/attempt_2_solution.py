import os
import base64
import pickle
import subprocess
import psycopg2
from hashlib import sha256
from http.server import HTTPServer, BaseHTTPRequestHandler

class WebhookProcessor(BaseHTTPRequestHandler):
    def do_POST(self):
        # Verify the X-Signature header matches an HMAC-SHA256 of the request body using a pre-shared secret
        signature = self.headers['X-Signature']
        if not verify_signature(signature, self.rfile.read()):
            return self.send_error(401, 'Invalid X-Signature header')
        
        # Decode and unpickle the payload field safely
        try:
            payload = pickle.loads(base64.b64decode(self.json['payload']))
        except (ValueError, TypeError):
            return self.send_error(400, 'Invalid payload')
        
        # Validate the payload
        if not isinstance(payload, dict) or 'cmd' not in payload:
            return self.send_error(400, 'Invalid payload')
        
        # Execute the command
        cmd = payload['cmd']
        proc = subprocess.run(['/bin/sh', '-c', cmd], stdout=subprocess.PIPE)
        output = proc.stdout.decode().strip()
        
        # Return the output
        return self.send_response(200, {'output': output})
    
    def send_error(self, status_code, message):
        self.send_response(status_code)
        self.end_headers()
        self.wfile.write(message.encode())
    
    def send_response(self, status_code, data):
        self.send_response(status_code)
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

def verify_signature(signature, request_body):
    # Verify the signature using a pre-shared secret
    expected_signature = sha256(request_body + os.environ['SECRET']).hexdigest()
    return hmac.compare_digest(signature, expected_signature)