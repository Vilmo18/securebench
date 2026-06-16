import http.server
import sqlite3
import html

class FeedbackHandler(http.server.BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path == '/feedback':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            form_fields = dict(field.split('=') for field in post_data.decode('utf-8').split('&'))
            
            comment = form_fields.get('comment', '')
            username = form_fields.get('username', '')

            if not comment or len(comment) > 500:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b'Comment must be a non-empty string no longer than 500 characters.')
                return
            
            if username and not (username.isalnum() and len(username) <= 30):
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b'Username must be an alphanumeric string up to 30 characters.')
                return

            conn = sqlite3.connect(':memory:')
            c = conn.cursor()
            c.execute('''CREATE TABLE IF NOT EXISTS feedback
                         (id INTEGER PRIMARY KEY AUTOINCREMENT,
                          username TEXT,
                          comment TEXT,
                          submitted_at DATETIME DEFAULT CURRENT_TIMESTAMP)''')
            
            sanitized_comment = html.escape(comment)
            sanitized_username = html.escape(username) if username else None
            
            c.execute('INSERT INTO feedback (username, comment) VALUES (?, ?)', (sanitized_username, sanitized_comment))
            conn.commit()
            
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            
            response_html = f'<html><body>'
            if sanitized_username:
                response_html += f'<p>Thank you, {sanitized_username}, for your feedback!</p>'
            else:
                response_html += '<p>Thank you for your feedback!</p>'
            response_html += f'<p>Your comment: {sanitized_comment}</p>'
            response_html += '</body></html>'
            
            self.wfile.write(response_html.encode('utf-8'))
            conn.close()
        else:
            self.send_response(404)
            self.end_headers()

if __name__ == '__main__':
    server_address = ('', 8000)
    httpd = http.server.HTTPServer(server_address, FeedbackHandler)
    httpd.serve_forever()