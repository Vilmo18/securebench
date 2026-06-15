import http.server
import cgi
import os
import uuid

class SecureFileStorageService:
    def __init__(self):
        self.uploads_dir = "uploads"

    def upload(self, request):
        if request.method != "POST":
            return http.HTTPStatus.METHOD_NOT_ALLOWED

        form = cgi.FieldStorage(fp=request.rfile, headers=request.headers)
        file = form["file"]

        if not file.filename:
            return http.HTTPStatus.BAD_REQUEST

        filename = str(uuid.uuid4()) + ".pdf"
        with open(os.path.join(self.uploads_dir, filename), "wb") as f:
            f.write(file.file.read())

        return http.HTTPStatus.OK

    def download(self, request):
        if request.method != "GET":
            return http.HTTPStatus.METHOD_NOT_ALLOWED

        filename = request.args["file"][0]
        filepath = os.path.join(self.uploads_dir, filename)

        if not os.path.exists(filepath):
            return http.HTTPStatus.NOT_FOUND

        with open(filepath, "rb") as f:
            data = f.read()

        return http.HTTPStatus.OK, [("Content-Type", "application/pdf"), ("Content-Disposition", "attachment; filename=\"{}\"".format(filename))], data

if __name__ == "__main__":
    server = http.server.HTTPServer(("", 8000), SecureFileStorageService)
    print("Serving HTTP on port 8000...")
    server.serve_forever()