import http.server
import cgi
import xml.etree.ElementTree as ET

users = {"user1", "user2", "user3"}
avatars = {}

class AvatarUploadHandler(http.server.BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path != '/upload/avatar':
            self.send_error(404)
            return

        form = cgi.FieldStorage(fp=self.rfile, headers=self.headers, environ={'REQUEST_METHOD':'POST'})

        user_id = form.getvalue('user_id')
        image_file = form['image_file']
        metadata_xml = form.getvalue('metadata_xml', '')

        if not user_id or user_id not in users:
            self.send_error(400, "Invalid user ID")
            return

        if not image_file.file or image_file.type not in ('image/png', 'image/jpeg') or len(image_file.value) > 2 * 1024 * 1024:
            self.send_error(400, "Invalid image file")
            return

        caption = None
        if metadata_xml:
            try:
                root = ET.fromstring(metadata_xml)
                ET.register_namespace('', 'http://www.w3.org/XML/1998/namespace')
                caption_element = root.find('caption')
                caption = caption_element.text if caption_element is not None else None
            except ET.ParseError:
                self.send_error(400, "Invalid XML metadata")
                return

        avatars[user_id] = {"image": image_file.file.read(), "caption": caption}

        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        response = {'status': 'success', 'user_id': user_id}
        self.wfile.write(bytes(json.dumps(response), 'utf-8'))

if __name__ == '__main__':
    server = http.server.HTTPServer(('', 8000), AvatarUploadHandler)
    print("Server running on port 8000")
    server.serve_forever()