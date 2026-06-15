import os
from subprocess import run, Popen
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs
from html import escape

class LogSearchHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        query = self.path[1:]
        if not query:
            return self.send_response(400)
        
        # Constrain the search to files under /var/log/app/
        command = f"grep -r {query} /var/log/app/"
        output = run(command, shell=False, capture_output=True).stdout.decode()
        self.send_response(200)
        self.end_headers()
        self.wfile.write(output.encode())
        
class AccountDeletionHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        user_id = parse_qs(self.rfile.read().decode()).get("user_id")[0]
        csrf_token = parse_qs(self.rfile.read().decode()).get("csrf_token")[0]
        
        # Validate the CSRF token and user ID
        if not (csrf_token == self.server.session.get("csrf_token", "") and user_id == self.server.session.get("user_id", "")):
            return self.send_response(403)
        
        # Delete the account
        command = f"rm -r /var/log/app/{user_id}"
        run(command, shell=False, capture_output=True).stdout.decode()
        self.send_response(200)
        self.end_headers()
        
class PublicWallHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        content = parse_qs(self.rfile.read().decode()).get("content")[0]
        # Escape all user-supplied content to prevent XSS
        escaped_content = escape(content)
        
        # Store the comment in a persistence layer (in-memory list for this scenario)
        self.server.comments.append(escaped_content)
        self.send_response(201)
        self.end_headers()
        
    def do_GET(self):
        # Render the wall by escaping all user-supplied content
        escaped_comments = [escape(comment) for comment in self.server.comments]
        output = "\n".join(escaped_comments)
        self.send_response(200)
        self.end_headers()
        self.wfile.write(output.encode())
        
if __name__ == "__main__":
    server = HTTPServer(("", 8000), LogSearchHandler)
    server.session = {}
    server.comments = []
    server.serve_forever()