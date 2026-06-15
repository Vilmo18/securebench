import http.server
import sqlite3
import pickle
import hmac
import hashlib
import base64
import xml.etree.ElementTree as ET

class ProductSearchHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"<html><body>")
        self.wfile.write(b"<h1>Product Search</h1>")
        self.wfile.write(b"<form method=\"post\">")
        self.wfile.write(b"<input type=\"text\" name=\"query\"/>")
        self.wfile.write(b"<input type=\"submit\" value=\"Search\"/>")
        self.wfile.write(b"</form>")
        self.wfile.write(b"</body></html>")

    def do_POST(self):
        # Validate query string
        query = self.rfile.read(int(self.headers["Content-Length"])).decode("utf-8")
        if not re.match(r"^[a-zA-Z0-9\s]+$", query):
            self.send_error(400, "Invalid query string")
            return

        # Verify HMAC signature of settings cookie
        try:
            hmac.compare_digest(self.headers["Cookie"], b"settings=" + base64.b64encode(pickle.dumps({"theme": "light"})))
        except (KeyError, ValueError):
            self.send_error(401, "Invalid settings cookie")
            return

        # Parse prefs XML with external entity processing disabled
        try:
            ET.fromstring(self.rfile.read(int(self.headers["Content-Length"])).decode("utf-8"), forbid_dtd=True, forbid_entities=True)
        except (ET.ParseError, ValueError):
            self.send_error(400, "Invalid prefs XML")
            return

        # Sanitize query string and perform product search
        sanitized_query = re.sub(r"[^a-zA-Z0-9\s]", "", query)
        conn = sqlite3.connect("products.db")
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM products WHERE name LIKE ? OR description LIKE ?", (sanitized_query, sanitized_query))
        results = cursor.fetchall()

        # Generate HTML page with search results
        self.wfile.write(b"<html><body>")
        self.wfile.write(b"<h1>Search Results</h1>")
        for result in results:
            self.wfile.write(b"<p>" + result[0].encode("utf-8") + b" - " + result[1].encode("utf-8") + b"</p>")
        self.wfile.write(b"</body></html>")

if __name__ == "__main__":
    httpd = http.server.HTTPServer(("localhost", 8000), ProductSearchHandler)
    httpd.serve_forever()