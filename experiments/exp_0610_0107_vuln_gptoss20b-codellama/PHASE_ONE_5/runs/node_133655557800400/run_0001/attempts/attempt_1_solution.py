import os
from pathlib import Path
from http.server import BaseHTTPRequestHandler, HTTPServer

class FileRetrievalHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        filename = self.path[1:]  # strip leading slash
        if not filename:
            return self.send_response(404)
        
        data_dir = Path("data")
        resolved_path = data_dir / filename
        if not resolved_path.is_file():
            return self.send_response(404)
        
        with open(resolved_path, "r") as f:
            content = f.read()
        
        self.send_response(200)
        self.end_headers()
        self.wfile.write(content.encode())