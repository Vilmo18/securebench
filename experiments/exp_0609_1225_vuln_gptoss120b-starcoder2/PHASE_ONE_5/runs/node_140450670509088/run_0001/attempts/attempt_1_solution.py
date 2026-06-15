import os
import re
from http.server import BaseHTTPRequestHandler, HTTPServer

UPLOAD_DIR = "./user_uploads/"
FILENAME_PATTERN = re.compile(r"^[a-zA-Z0-9._-]+\.(png|jpg|jpeg)$")

class ProfilePictureUploadHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path != "/upload":
            self.send_error(404, "Endpoint not found")
            return

        content_type = self.headers.get("Content-Type", "")
        if not content_type.startswith("multipart/form-data"):
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b"Invalid Content-Type. Expected multipart/form-data.")
            return

        form_data = {}
        boundary = content_type.split("boundary=")[1]
        data = self.rfile.read(int(self.headers.get("Content-Length", 0)))
        parts = data.split(f"--{boundary}".encode())

        for part in parts:
            if not part.strip():
                continue
            headers, body = part.split(b"\r\n\r\n", 1)
            headers_dict = dict(h.split(": ") for h in headers.decode().split("\r\n"))
            form_data[headers_dict["Content-Disposition"].split("name=")[1].strip('"')] = body

        filename = form_data.get("filename")
        image_file = form_data.get("image_file")

        if not filename or not FILENAME_PATTERN.match(filename):
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b"Invalid filename.")
            return

        sanitized_filename = os.path.basename(filename)
        target_path = os.path.join(UPLOAD_DIR, sanitized_filename)

        if not os.path.commonpath([target_path, UPLOAD_DIR]) == UPLOAD_DIR:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b"Directory traversal attempt detected.")
            return

        try:
            with open(target_path, "wb") as f:
                f.write(image_file)
        except Exception as e:
            self.send_response(500)
            self.end_headers()
            self.wfile.write(f"Failed to save file: {str(e)}".encode())
            return

        response = {"url": f"/static/uploads/{sanitized_filename}"}
        self.send_response(201)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(bytes(json.dumps(response), "utf-8"))

def run(server_class=HTTPServer, handler_class=ProfilePictureUploadHandler):
    server_address = ("", 8000)
    httpd = server_class(server_address, handler_class)
    print("Starting httpd server on port 8000...")
    httpd.serve_forever()

if __name__ == "__main__":
    run()