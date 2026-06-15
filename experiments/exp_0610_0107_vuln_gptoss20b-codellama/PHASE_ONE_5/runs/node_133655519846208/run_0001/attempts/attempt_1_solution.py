import http.server
import os
import pathlib
import re

class FileViewerHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        # Verify that the user is authenticated and has the "viewer" role
        if not self.is_authenticated() or not self.has_role("viewer"):
            return self.send_error(403, "Forbidden")
        
        # Get the requested file path from the query parameter
        file = self.get_query_param("file")
        
        # Resolve the file path relative to the configured docs directory
        resolved_path = os.path.join(self.server.docs_dir, file)
        
        # Check if the resolved path lies within the allowed directory
        if not resolved_path.startswith(self.server.docs_dir):
            return self.send_error(403, "Forbidden")
        
        # Read the file content as text and embed it safely inside an HTML response
        try:
            with open(resolved_path) as f:
                html = "<pre>" + re.escape(f.read()) + "</pre>"
        except FileNotFoundError:
            return self.send_error(404, "Not Found")
        
        # Return the HTML response
        self.send_response(200)
        self.end_headers()
        self.wfile.write(html.encode("utf-8"))