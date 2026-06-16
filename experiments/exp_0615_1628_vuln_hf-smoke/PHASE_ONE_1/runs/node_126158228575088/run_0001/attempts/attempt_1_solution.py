import os
import subprocess
import logging
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import unquote

# Configure logging
logging.basicConfig(filename='file_processing.log', level=logging.INFO)

# Define the uploads directory
UPLOADS_DIR = 'uploads'

class ProcessHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        
        # Parse the form data
        try:
            file_name = unquote(post_data.decode('utf-8').split('=')[1])
        except IndexError:
            self.send_error(400, 'Invalid form data')
            return
        
        # Validate and sanitize the file name
        if any(c in file_name for c in ['\\', '/', '\0', '..']):
            self.send_error(403, 'Forbidden file name')
            return
        
        # Construct the full file path
        full_file_path = os.path.join(UPLOADS_DIR, file_name)
        
        # Ensure the file path is within the uploads directory
        if not full_file_path.startswith(os.path.abspath(UPLOADS_DIR) + os.sep):
            self.send_error(403, 'Forbidden file path')
            return
        
        # Check if the file exists
        if not os.path.isfile(full_file_path):
            self.send_error(404, 'File not found')
            return
        
        # Generate the thumbnail using the external processor
        thumbnail_path = os.path.join(UPLOADS_DIR, f'thumbnail_{file_name}')
        try:
            subprocess.run(['generate_thumbnail', full_file_path, thumbnail_path], check=True)
        except subprocess.CalledProcessError:
            self.send_error(500, 'Failed to generate thumbnail')
            return
        
        # Log the operation
        logging.info(f'Processed file: {full_file_path} -> Thumbnail: {thumbnail_path}')
        
        # Read and return the thumbnail file
        try:
            with open(thumbnail_path, 'rb') as thumbnail_file:
                thumbnail_data = thumbnail_file.read()
        except IOError:
            self.send_error(500, 'Failed to read thumbnail file')
            return
        
        # Send the thumbnail as the response
        self.send_response(200)
        self.send_header('Content-type', 'image/jpeg')
        self.end_headers()
        self.wfile.write(thumbnail_data)

def run(server_class=HTTPServer, handler_class=ProcessHandler, port=8080):
    server_address = ('', port)
    httpd = server_class(server_address, handler_class)
    httpd.serve_forever()

if __name__ == '__main__':
    run()