import http.server, cgi, json, xml.etree.ElementTree
from defusedxml import ElementTree
from pathlib import Path

class UploadHandler(http.server.BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path == "/admin/upload":
            form = cgi.FieldStorage(fp=self.rfile, headers=self.headers)
            config_xml = form.getvalue("config.xml")
            data_json = form.getvalue("data.json")
            csrf_token = form.getvalue("csrf_token")
            
            if not all([config_xml, data_json, csrf_token]):
                self.send_error(400)
                return
                
            # Validate filenames
            for filename in [config_xml, data_json]:
                if "/" in filename or "\\" in filename or "\x00" in filename:
                    self.send_error(400)
                    return
            
            # Write files to disk
            with open(Path("/var/app/uploads") / config_xml, "wb") as f:
                f.write(config_xml.encode("utf-8"))
            with open(Path("/var/app/uploads") / data_json, "wb") as f:
                f.write(data_json.encode("utf-8"))
            
            # Parse config XML
            tree = ElementTree.parse(config_xml)
            root = tree.getroot()
            for child in root:
                if child.tag == "user":
                    user_id = int(child.findtext("id"))
                    preferences = json.loads(child.findtext("preferences"))
                    roles = [int(role) for role in child.findall("roles/role")]
            
            # Deserialize data JSON
            try:
                data = json.loads(data_json)
            except json.JSONDecodeError:
                self.send_error(400)
                return
                
            if not all([user_id, preferences, roles]):
                self.send_error(400)
                return
            
            # Enforce CSRF protection
            session = http.server.Session()
            if csrf_token != session["csrf_token"]:
                self.send_error(403)
                return
                
            # Update runtime settings
            # ...
            
            self.send_response(200)
            self.end_headers()
        else:
            self.send_error(404)