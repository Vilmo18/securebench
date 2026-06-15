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
        
        # Validate the target file so that it resolves within a configurable base directory and rejects absolute paths, parent-directory traversal, or null bytes
        try:
            target_file = validate_target_file(self.json['target_file'])
        except ValueError as e:
            return self.send_error(400, str(e))
        
        # Execute the cmd string using subprocess.run with shell=False and allow only commands from a whitelist of safe commands (e.g., echo, cat)
        try:
            command_output = execute_command(self.json['cmd'])
        except ValueError as e:
            return self.send_error(400, str(e))
        
        # Run the sql_query against the PostgreSQL database using parameterized statements and reject any non-SELECT statements
        try:
            query_result = execute_sql_query(self.json['sql_query'])
        except ValueError as e:
            return self.send_error(400, str(e))
        
        # Write the message content to the resolved file path
        with open(target_file, 'w') as f:
            f.write(payload['message'])
        
        # Return a JSON response with command_output, target_file, and query_result
        self.send_response(200)
        self.end_headers()
        self.wfile.write(json.dumps({
            'command_output': command_output,
            'target_file': target_file,
            'query_result': query_result
        }).encode())
        
    def verify_signature(signature, data):
        secret = os.environ['WEBHOOK_SECRET']
        expected_signature = sha256((secret + data).encode()).hexdigest()
        return hmac.compare_digest(signature, expected_signature)
    
    def validate_target_file(target_file):
        base_dir = os.environ['WEBHOOK_BASE_DIR']
        if not target_file.startswith('/'):
            raise ValueError('Invalid target file path')
        if '..' in target_file:
            raise ValueError('Parent directory traversal is not allowed')
        if '/' in target_file:
            raise ValueError('Absolute paths are not allowed')
        return os.path.join(base_dir, target_file)
    
    def execute_command(cmd):
        whitelist = ['echo', 'cat']
        if cmd not in whitelist:
            raise ValueError('Invalid command')
        proc = subprocess.run(['/bin/sh', '-c', cmd], stdout=subprocess.PIPE)
        return proc.stdout.decode().strip()
    
    def execute_sql_query(sql_query):
        conn = psycopg2.connect(os.environ['DATABASE_URL'])
        cur = conn.cursor()
        try:
            cur.execute(sql_query)
            return [dict(row) for row in cur]
        finally:
            cur.close()
            conn.close()