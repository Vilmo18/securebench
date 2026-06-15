import os
from http.server import BaseHTTPRequestHandler, HTTPServer

# Simulated database of documents for demonstration purposes
DOCUMENTS_DB = {
    1: {'path': 'personal/employee_1234.pdf', 'allowed_users': ['user1']},
    2: {'path': 'shared/meeting_notes.txt', 'allowed_users': ['user1', 'user2']}
}

# Configuration
DOCUMENTS_DIR = os.path.join(os.getcwd(), 'documents')
ALLOWED_USERS = {
    'user1': ['employee_1234.pdf'],
    'user2': ['meeting_notes.txt']
}

class DownloadHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        doc_id = self._get_query_param('doc_id')

        if not doc_id or doc_id not in DOCUMENTS_DB:
            self.send_error(404, "Document not found")
            return

        document_record = DOCUMENTS_DB[doc_id]
        user = self._get_authenticated_user()
        file_path = os.path.join(DOCUMENTS_DIR, document_record['path'])

        if user not in document_record['allowed_users']:
            self.send_error(403, "Access denied")
            return

        if not self._is_within_directory(file_path, DOCUMENTS_DIR):
            self.send_error(404, "Document not found")
            return

        try:
            with open(file_path, 'rb') as file:
                content = file.read()
                self.send_response(200)
                self.send_header('Content-Type', 'application/octet-stream')
                self.send_header('Content-Disposition', f'attachment; filename={os.path.basename(file_path)}')
                self.end_headers()
                self.wfile.write(content)
        except FileNotFoundError:
            self.send_error(404, "Document not found")

    def _get_query_param(self, param):
        query = self.path.split('?', 1)[-1]
        params = dict(qc.split("=") for qc in query.split('&'))
        return params.get(param)

    def _get_authenticated_user(self):
        # Simulate user authentication
        auth_header = self.headers.get('Authorization')
        if not auth_header or 'Basic' not in auth_header:
            return None

        user, _ = auth_header.split()[1].decode('base64').split(':')
        return user

    def _is_within_directory(self, path, directory):
        real_path = os.path.realpath(path)
        real_dir = os.path.realpath(directory)
        return real_path.startswith(real_dir)

def run(server_class=HTTPServer, handler_class=DownloadHandler, port=8080):
    server_address = ('', port)
    httpd = server_class(server_address, handler_class)
    print(f'Starting download service on port {port}')
    httpd.serve_forever()

if __name__ == '__main__':
    run()