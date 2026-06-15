import xml.etree.ElementTree as ET
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse
from pathlib import Path
from defusedxml.common import DefusedXmlException
from defusedxml.ElementTree import parse

class AuthHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path == '/auth/login':
            # Parse the XML request body using a secure parser
            try:
                tree = parse(self.rfile)
            except DefusedXmlException as e:
                print("Error parsing XML:", e)
                self.send_response(401)
                self.end_headers()
                return
            
            root = tree.getroot()
            
            # Extract the username, password, role, and profile_path from the XML
            username = root.find('username').text
            password = root.find('password').text
            role = root.find('role').text
            profile_path = root.find('profile_path').text
            
            # Verify credentials against a predefined in-memory user store
            if username not in USERS or password != USERS[username]:
                self.send_response(401)
                self.end_headers()
                return
            
            # Map the supplied role to a set of permissions
            permissions = ROLES[role]
            
            # Only allow retrieval of profile files that reside inside the user’s own profiles/ directory
            if '..' in profile_path or not profile_path.startswith(f'{username}/profiles/'):
                self.send_response(403)
                self.end_headers()
                return
            
            # Read the file once and return its contents with a JSON Content-Type
            try:
                with open(profile_path, 'r') as f:
                    profile = json.load(f)
            except FileNotFoundError:
                self.send_response(403)
                self.end_headers()
                return
            
            # Return the profile data with a JSON Content-Type header
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(profile).encode())
        else:
            self.send_response(404)
            self.end_headers()
            
if __name__ == '__main__':
    # Define the predefined in-memory user store and role mapping
    USERS = {
        'alice': 'password1',
        'bob': 'password2'
    }
    
    ROLES = {
        'admin': ['read', 'write'],
        'user': ['read']
    }
    
    # Start the HTTP server and listen for requests
    httpd = HTTPServer(('localhost', 8000), AuthHandler)
    print("Server started")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()