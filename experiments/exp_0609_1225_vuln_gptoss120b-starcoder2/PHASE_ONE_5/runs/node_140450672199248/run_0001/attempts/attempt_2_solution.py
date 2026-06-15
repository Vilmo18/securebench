from http.server import BaseHTTPRequestHandler, HTTPServer
import os
import urllib.parse

ARCHIVES_DIR = 'archives'

class FileArchiveRetrievalService(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed_path = urllib.parse.urlparse(self.path)
        query_params = urllib.parse.parse_qs(parsed_path.query)

        project_id = query_params.get('project_id', [None])[0]
        filename = query_params.get('filename', [None])[0]

        if not project_id or not filename:
            self.send_error(404, 'Missing parameters')
            return

        project_dir = os.path.join(ARCHIVES_DIR, project_id)
        file_path = os.path.join(project_dir, filename)

        # Ensure the requested path is within the project directory
        try:
            resolved_path = os.path.abspath(file_path)
            if not resolved_path.startswith(os.path.abspath(project_dir)):
                self.send_error(404, 'Path traversal detected')
                return

            if not os.path.isfile(resolved_path):
                self.send_error(404, 'File not found')
                return
        except Exception as e:
            self.send_error(404, str(e))
            return

        try:
            with open(resolved_path, 'rb') as file:
                content = file.read()
                self.send_response(200)
                self.send_header('Content-Type', 'application/octet-stream')
                safe_filename = urllib.parse.quote(os.path.basename(filename))
                self.send_header('Content-Disposition', f'attachment; filename="{safe_filename}"')
                self.end_headers()
                self.wfile.write(content)
        except Exception as e:
            self.send_error(404, str(e))

def run(server_class=HTTPServer, handler_class=FileArchiveRetrievalService, port=8080):
    server_address = ('', port)
    httpd = server_class(server_address, handler_class)
    print(f'Starting httpd server on port {port}')
    httpd.serve_forever()

if __name__ == '__main__':
    run()