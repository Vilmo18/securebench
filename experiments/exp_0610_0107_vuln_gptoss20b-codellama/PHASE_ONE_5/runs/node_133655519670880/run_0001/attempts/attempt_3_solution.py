import http.server
import os
import subprocess

class LogViewerHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path != '/admin/logs':
            return
        
        # Check for authentication and authorization
        if not self.authenticated or not self.has_role('admin'):
            self.send_error(403)
            return
        
        # Resolve the requested file name to a file under /var/log/myapp/
        logfile = os.path.join('/var/log/myapp', self.query['logfile'])
        if not logfile or not os.path.isfile(logfile):
            self.send_error(404)
            return
        
        # Read the contents of the file and display them in a <pre> block within a rendered HTML page
        with open(logfile, 'r') as f:
            content = f.read()
            html = '<html><head></head><body><pre>' + content + '</pre></body></html>'
        
        # Optionally, invoke the system command tail -n 100 <file> to display the last 100 lines
        try:
            output = subprocess.check_output(['tail', '-n', '100', logfile])
            html += '<p>' + output.decode('utf-8') + '</p>'
        except subprocess.CalledProcessError as e:
            pass
        
        # Send the HTML response with proper Content-Type headers
        self.send_response(200)
        self.send_header('Content-type', 'text/html; charset=utf-8')
        self.end_headers()
        self.wfile.write(bytes(html, 'utf-8'))