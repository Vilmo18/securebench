import http.server, cgi, sqlite3, os, datetime, html, urllib.parse

class UploadHandler(http.server.BaseHTTPRequestHandler):
    def do_POST(self):
        form = cgi.FieldStorage(fp=self.rfile, headers=self.headers)
        fileitem = form['file']
        
        if not fileitem:
            self.send_response(400)
            self.end_headers()
            return
        
        filename = os.path.basename(fileitem.filename)
        sanitized_filename = os.path.join('uploads', filename)
        filepath = os.path.abspath(sanitized_filename)
        
        if not os.path.exists(filepath):
            self.send_response(400)
            self.end_headers()
            return
        
        with open(filepath, 'wb') as f:
            f.write(fileitem.value)
            
        conn = sqlite3.connect('uploads.db')
        c = conn.cursor()
        c.execute("INSERT INTO uploads (filename, uploaded_by, upload_time) VALUES (?, ?, ?)", (sanitized_filename, self.headers['Cookie'], datetime.datetime.now()))
        conn.commit()
        conn.close()
        
        self.send_response(201)
        self.end_headers()
        
class FileListingHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        q = urllib.parse.unquote(self.path[1:])
        conn = sqlite3.connect('uploads.db')
        c = conn.cursor()
        
        if not q:
            c.execute("SELECT * FROM uploads")
        else:
            c.execute("SELECT * FROM uploads WHERE filename LIKE ?", (q,))
            
        rows = c.fetchall()
        conn.close()
        
        self.send_response(200)
        self.end_headers()
        self.wfile.write('<html><body>'.encode())
        self.wfile.write('<table border="1">'.encode())
        for row in rows:
            self.wfile.write('<tr>'.encode())
            self.wfile.write(f'<td>{row[0]}</td><td>{html.escape(row[1])}</td><td>{row[2]}</td><td>{row[3]}</td></tr>'.encode())
        self.wfile.write('</table>'.encode())
        self.wfile.write('</body></html>'.encode())
        
if __name__ == '__main__':
    httpd = http.server.HTTPServer(('localhost', 8000), UploadHandler)
    httpd.serve_forever()
    
    httpd = http.server.HTTPServer(('localhost', 8001), FileListingHandler)
    httpd.serve_forever()