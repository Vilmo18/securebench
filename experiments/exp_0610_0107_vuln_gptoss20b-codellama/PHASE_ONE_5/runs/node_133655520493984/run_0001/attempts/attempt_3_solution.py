import http.server, cgi, xml.etree.ElementTree as ET, pickle, base64, subprocess, os, pathlib
from defusedxml import defuse_stdlib

class ConfigHandler(http.server.BaseHTTPRequestHandler):
    def do_POST(self):
        form = cgi.FieldStorage(fp=self.rfile, headers=self.headers)
        config = ET.fromstring(form['config.xml'].value)
        
        # Validate the XML file against a schema
        if not self.validate_schema(config):
            return
        
        # Execute the command specified in the XML file
        command = config.findtext('command')
        subprocess.run(command, shell=False)
        
        # Log the execution of the command
        log_file = os.path.join(os.getcwd(), 'logs', 'execution_log.txt')
        with open(log_file, 'a') as f:
            f.write('Command executed: {}\n'.format(command))
        
        # Return a success message to the client
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'Successfully executed command')
    
    def validate_schema(self, config):
        schema = ET.parse('config.xsd')
        return schema.validate(config)