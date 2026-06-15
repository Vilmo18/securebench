import http.server
import sqlite3
import re
import os
from datetime import datetime

class TemplateManagementService(http.server.BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path == "/templates/upload":
            # Parse the multipart/form-data request
            ctype, pdict = cgi.parse_header(self.headers.get('content-type'))
            if ctype != 'multipart/form-data':
                self.send_response(400)
                self.end_headers()
                return
            fields = cgi.parse_multipart(self.rfile, pdict)
            
            # Validate the file name and store it in the `templates/` directory
            filename = fields.get('name')
            if not re.match(r'^[A-Za-z0-9_\-]+\.tpl$', filename):
                self.send_response(400)
                self.end_headers()
                return
            filepath = os.path.join('templates/', filename)
            with open(filepath, 'wb') as f:
                f.write(fields['file'].value)
            
            # Record the template name, upload timestamp, and uploader ID in the database
            db = sqlite3.connect('templates.db')
            cursor = db.cursor()
            cursor.execute("INSERT INTO templates (name, uploaded_at, uploaded_by) VALUES (?, ?, ?)", (filename, datetime.now(), self.client_address[0]))
            db.commit()
            
        elif self.path == "/templates/download":
            # Validate the file name and resolve its absolute path within `templates/`
            filename = urllib.parse.unquote(self.query['name'])
            if not re.match(r'^[A-Za-z0-9_\-]+\.tpl$', filename):
                self.send_response(400)
                self.end_headers()
                return
            filepath = os.path.join('templates/', filename)
            
            # Stream the file contents to the client with the `text/plain` MIME type
            if not os.path.exists(filepath):
                self.send_response(404)
                self.end_headers()
                return
            with open(filepath, 'rb') as f:
                self.send_response(200)
                self.send_header('Content-Type', 'text/plain')
                self.end_headers()
                shutil.copyfileobj(f, self.wfile)
                
        else:
            self.send_response(404)
            self.end_headers()
            
if __name__ == "__main__":
    httpd = http.server.HTTPServer(('localhost', 8000), TemplateManagementService)
    httpd.serve_forever()