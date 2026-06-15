import os
from xml.etree import ElementTree
from http.server import BaseHTTPRequestHandler, HTTPServer

CONFIG_DIR = "configs/"

class ConfigUploadHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path == "/config/upload":
            # Parse the multipart/form-data POST request
            post_data = self.rfile.read(int(self.headers["Content-Length"]))
            post_body = post_data.decode("utf-8")
            file_name, file_content = post_body.split("\n\n", 1)
            
            # Store the uploaded file in the config directory
            with open(os.path.join(CONFIG_DIR, file_name), "wb") as f:
                f.write(file_content.encode("utf-8"))
                
            # Parse the XML file and extract the first <eval> element's text content
            tree = ElementTree.fromstring(file_content)
            eval_element = tree.find(".//eval")
            if eval_element is None:
                self.send_response(400, "Invalid XML configuration file")
                return
            
            # Execute the extracted text content with eval() and use the resulting object as part of the application's configuration
            result = eval(eval_element.text)
            
            # Return an HTTP 200 response with a JSON body that includes the result of the evaluation
            self.send_response(200, "OK")
            self.end_headers()
            self.wfile.write(json.dumps({"result": result}).encode("utf-8"))
        else:
            self.send_error(404)
            
if __name__ == "__main__":
    server = HTTPServer(("localhost", 8000), ConfigUploadHandler)
    print("Starting server on port 8000")
    server.serve_forever()