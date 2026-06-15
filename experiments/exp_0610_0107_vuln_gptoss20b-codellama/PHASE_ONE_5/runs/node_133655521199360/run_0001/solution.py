import os
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs

class AdminCommandExecutor(BaseHTTPRequestHandler):
    def do_POST(self):
        # Parse the form data
        form = parse_qs(self.rfile.read(int(self.headers['Content-Length'])))
        
        # Check if the request includes a valid session cookie
        if not self.check_session():
            return self.send_error(403, 'Forbidden')
        
        # Validate the command and CSRF token
        if not self.validate_command(form['command'][0]) or not self.validate_csrf_token(form['csrf_token'][0]):
            return self.send_error(400, 'Bad Request')
        
        # Execute the command and capture its output
        try:
            result = subprocess.run(form['command'][0], shell=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        except Exception as e:
            return self.send_error(500, 'Internal Server Error')
        
        # Return the result as a JSON response
        self.send_response(200)
        self.end_headers()
        self.wfile.write(json.dumps({'exit_status': result.returncode, 'stdout': result.stdout.decode(), 'stderr': result.stderr.decode()}).encode())
        
    def check_session(self):
        # Check if the request includes a valid session cookie
        return self.headers.get('Cookie', None) and self.headers['Cookie'].startswith('session=')
    
    def validate_command(self, command):
        # Validate that the submitted command is one of the approved identifiers
        return command in ['restart_service', 'backup_db', 'clear_cache']
    
    def validate_csrf_token(self, token):
        # Confirm that the supplied CSRF token matches the token stored on the server for the current session
        return token == self.session['csrf_token']