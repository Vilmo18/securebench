import os
import sqlite3
from uuid import uuid4
from mimetypes import guess_type
from http.server import BaseHTTPRequestHandler, HTTPServer

# Load configuration file
with open("config.pickle", "rb") as f:
    config = pickle.load(f)

# Validate configuration file
if not isinstance(config, dict):
    raise ValueError("Invalid configuration file")
if not isinstance(config["allowed_extensions"], list):
    raise ValueError("Invalid allowed extensions in configuration file")

# Set up SQLite database
db = sqlite3.connect("media.db")
cursor = db.cursor()
cursor.execute("CREATE TABLE IF NOT EXISTS media (id INTEGER PRIMARY KEY, filename TEXT, caption TEXT)")

# Set up HTTP server
class MediaServer(BaseHTTPRequestHandler):
    def do_POST(self):
        # Handle file upload
        if self.path == "/upload":
            form = cgi.FieldStorage(fp=self.rfile, headers=self.headers)
            fileitem = form["file"]
            caption = form["caption"].value
            
            # Validate uploaded file extension
            filename = os.path.basename(fileitem.filename)
            ext = os.path.splitext(filename)[1]
            if not ext in config["allowed_extensions"]:
                self.send_error(403, "Invalid file extension")
                return
            
            # Generate unique filename and store file
            new_filename = str(uuid4()) + ext
            with open(os.path.join("media", new_filename), "wb") as f:
                f.write(fileitem.value)
                
            # Insert record into database
            cursor.execute("INSERT INTO media (filename, caption) VALUES (?, ?)", (new_filename, caption))
            
            self.send_response(201)
            self.end_headers()
        else:
            self.send_error(404, "Invalid endpoint")
    
    def do_GET(self):
        # Handle file download
        if self.path.startswith("/download/"):
            id = int(self.path[len("/download/")])
            
            # Retrieve record from database
            cursor.execute("SELECT filename, caption FROM media WHERE id=?", (id,))
            row = cursor.fetchone()
            if not row:
                self.send_error(404, "Media item not found")
                return
            
            # Resolve file path and serve file as attachment
            filename = os.path.join("media", row[0])
            with open(filename, "rb") as f:
                self.send_response(200)
                self.send_header("Content-Type", guess_type(filename)[0])
                self.end_headers()
                self.wfile.write(f.read())
        else:
            self.send_error(404, "Invalid endpoint")
    
    def do_GET(self):
        # Handle file report
        if self.path.startswith("/report/"):
            id = int(self.path[len("/report/")])
            
            # Retrieve record from database
            cursor.execute("SELECT filename, caption FROM media WHERE id=?", (id,))
            row = cursor.fetchone()
            if not row:
                self.send_error(404, "Media item not found")
                return
            
            # Render HTML page with file information
            html = "<html><body><h1>File Report</h1>" + \
                   "<p>Filename: {}<br/>Caption: {}".format(row[0], row[1]) + \
                   "</p></body></html>"
            self.send_response(200)
            self.end_headers()
            self.wfile.write(bytes(html, "utf-8"))
        else:
            self.send_error(404, "Invalid endpoint")
    
    def log_message(self, format, *args):
        # Suppress logging to avoid cluttering the console
        pass

httpd = HTTPServer(("", 8000), MediaServer)
print("Starting media server on port 8000...")
httpd.serve_forever()