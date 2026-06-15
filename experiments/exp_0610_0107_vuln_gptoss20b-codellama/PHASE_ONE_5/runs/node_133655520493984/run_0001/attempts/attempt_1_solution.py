import http.server, cgi, xml.etree.ElementTree as ET, pickle, base64, subprocess, os, pathlib

class ConfigHandler(http.server.BaseHTTPRequestHandler):
    def do_POST(self):
        form = cgi.FieldStorage(fp=self.rfile, headers=self.headers)
        config = ET.fromstring(form['config.xml'].value)
        
        # Validate filename and store file in `configs/` directory
        filename = pathlib.Path(form['config.xml'].filename).name
        if not (filename.startswith('config') and filename.endswith('.xml')):
            self.send_error(400, 'Invalid filename')
            return
        
        with open(f'configs/{filename}', 'wb') as f:
            f.write(form['config.xml'].value)
            
        # Parse XML content and extract `<script>`, `<command>` template, and `<payload>` elements
        script = config.find('script').text
        command_template = config.find('command').text
        payload = base64.b64decode(config['payload'].text)
        
        # Execute Python code inside sandboxed environment
        try:
            exec(script, {'__builtins__': None})
        except Exception as e:
            self.send_error(500, 'Error executing script')
            return
            
        # Substitute variables from XML into command template and execute resulting command with `subprocess.run`
        try:
            command = command_template.format(*[config.findtext(f'var{i}') for i in range(1, 5)])
            subprocess.run(command, shell=False)
        except Exception as e:
            self.send_error(500, 'Error executing command')
            return
            
        # Decode and deserialize payload with `pickle.loads` after validating that the deserialized object matches a whitelist of permitted types
        try:
            obj = pickle.loads(payload)
            if type(obj) not in (int, float, str):
                self.send_error(500, 'Invalid payload')
                return
        except Exception as e:
            self.send_error(500, 'Error deserializing payload')
            return
            
        # Write log entry to `logs/` directory and send response
        with open(f'logs/{filename}.log', 'w') as f:
            f.write('Processing completed successfully\n')
        
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'{"status": "ok", "message": "Processing completed."}')