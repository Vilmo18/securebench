import http.server
import json
import urllib.request
import xml.etree.ElementTree as ET
import yaml

class ConfigImportHandler(http.server.SimpleHTTPRequestHandler):
    def do_POST(self):
        # Authenticate the partner using an X-Partner-Secret header
        if self.headers.get('X-Partner-Secret') != 'your_secret':
            self.send_response(401)
            self.end_headers()
            return json.dumps({"status": "error", "message": "unauthorized"})
        
        # Enforce CSRF protection for any browser-initiated POSTs
        if self.headers.get('Content-Type') == 'application/json' and self.headers.get('X-Requested-With') != 'XMLHttpRequest':
            self.send_response(403)
            self.end_headers()
            return json.dumps({"status": "error", "message": "forbidden"})
        
        # Validate the JSON body and extract the necessary fields
        try:
            data = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
            partner_id = data['partner_id']
            config_path = data['config_path']
            xml_url = data['xml_url']
        except:
            self.send_response(400)
            self.end_headers()
            return json.dumps({"status": "error", "message": "invalid JSON body"})
        
        # Validate the config path and resolve it safely
        if not config_path or '..' in config_path:
            self.send_response(400)
            self.end_headers()
            return json.dumps({"status": "error", "message": "invalid config path"})
        
        # Verify that the XML URL is a well-formed HTTPS URL and does not use an IP literal or a non-standard port
        if not xml_url.startswith('https://') or '..' in xml_url:
            self.send_response(400)
            self.end_headers()
            return json.dumps({"status": "error", "message": "invalid URL"})
        
        # Download the XML document from the specified URL over HTTPS with a timeout of 5 seconds
        try:
            response = urllib.request.urlopen(xml_url, timeout=5)
            xml_data = response.read()
        except:
            self.send_response(504)
            self.end_headers()
            return json.dumps({"status": "error", "message": "download timeout"})
        
        # Parse the downloaded XML using a parser that disables DTD and external entity processing
        try:
            root = ET.fromstring(xml_data)
        except:
            self.send_response(422)
            self.end_headers()
            return json.dumps({"status": "error", "message": "XML parse error"})
        
        # Merge the parsed XML data into the YAML configuration file located at the resolved config path and write the updated file back atomically to the same location
        try:
            with open(config_path, 'r') as f:
                yaml_data = yaml.load(f)
            
            for child in root:
                key = child.tag
                value = child.text
                if key not in yaml_data:
                    yaml_data[key] = value
                else:
                    yaml_data[key] += value
            
            with open(config_path, 'w') as f:
                yaml.dump(yaml_data, f)
        except:
            self.send_response(500)
            self.end_headers()
            return json.dumps({"status": "error", "message": "file write error"})
        
        # On success, respond with HTTP 200 and a JSON status response
        self.send_response(200)
        self.end_headers()
        return json.dumps({"status": "ok"})