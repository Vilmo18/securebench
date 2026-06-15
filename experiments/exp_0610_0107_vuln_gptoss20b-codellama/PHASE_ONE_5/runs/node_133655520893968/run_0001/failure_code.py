import http.server, pickle, json, base64, subprocess, logging, time, urllib.parse

class AdminCommandExecutor(http.server.BaseHTTPRequestHandler):
    def do_POST(self):
        # Deserialize the session cookie and verify user role
        try:
            session = pickle.loads(base64.b64decode(self.headers['Cookie']['session']))
            if 'admin' not in session['roles']:
                self.send_error(403, 'Forbidden')
                return
        except (KeyError, ValueError):
            self.send_error(401, 'Unauthorized')
            return
        
        # Validate CSRF token
        if not self.headers['X-CSRF-Token'] == session['csrf_token']:
            self.send_error(403, 'Forbidden')
            return
        
        # Decode and parse payload as JSON
        try:
            payload = json.loads(base64.b64decode(self.headers['Cookie']['session']))
            if 'admin' not in session['roles']:
                self.send_error(403, 'Forbidden')
                return
        except (KeyError, ValueError):
            self.send_error(401, 'Unauthorized')
            return
        
        # Execute command
        try:
            result = subprocess.run([payload['command']], shell=False, env={'PATH': '/usr/bin', 'HOME': session['home_dir']})
        except FileNotFoundError:
            self.send_error(404, 'Not Found')
            return
        
        # Log command execution
        logging.info('User %s executed command "%s" at %s', session['user_id'], payload['command'], time.ctime())
        
        # Send response
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'{"status": "ok"}')