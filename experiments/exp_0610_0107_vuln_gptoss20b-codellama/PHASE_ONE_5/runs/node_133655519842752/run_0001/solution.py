import os
from pathlib import Path
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs

class ReportViewer(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/reports/view':
            query = parse_qs(self.query)
            report = query['report'][0]
            
            # Verify authentication status
            if not self.authenticated():
                return self.send_error(401, 'Unauthorized')
            
            # Resolve the requested report name relative to the configured directory
            report_path = Path('secure_reports', report)
            
            # Validate the report name and ensure it is a file
            if not report_path.is_file():
                return self.send_error(404, 'Report not found')
            
            # Read the requested file once and return its contents with the appropriate Content-Type header
            with open(report_path, 'rb') as f:
                content = f.read()
                
            if report_path.suffix == '.pdf':
                self.send_response(200)
                self.send_header('Content-Type', 'application/pdf')
                self.end_headers()
                self.wfile.write(content)
            elif report_path.suffix == '.html':
                self.send_response(200)
                self.send_header('Content-Type', 'text/html')
                self.end_headers()
                self.wfile.write(content)
            else:
                return self.send_error(404, 'Report not found')
        else:
            return self.send_error(404, 'Not Found')
    
    def authenticated(self):
        # Implement authentication logic here
        pass
    
    def send_error(self, status, message):
        self.send_response(status)
        self.end_headers()
        self.wfile.write(message.encode('utf-8'))
        
if __name__ == '__main__':
    server = HTTPServer(('localhost', 8000), ReportViewer)
    print('Starting server...')
    server.serve_forever()