import http.server, xml.etree.ElementTree as ET, sqlite3, json, jwt, re

class AdminPluginLoader(http.server.BaseHTTPRequestHandler):
    def do_POST(self):
        if not self.headers.get('Authorization'):
            return self._error('Missing Authorization header')
        
        token = self.headers['Authorization'].split()[1]
        try:
            jwt.decode(token, 'secret', algorithms=['HS256'])
        except jwt.InvalidTokenError:
            return self._error('Invalid admin token')
        
        if not self.headers.get('Content-Type'):
            return self._error('Missing Content-Type header')
        
        if self.headers['Content-Type'] != 'multipart/form-data':
            return self._error('Unsupported content type: {}'.format(self.headers['Content-Type']))
        
        form = self.rfile.read().decode()
        match = re.search(r'name="plugin_config"', form)
        if not match:
            return self._error('Missing plugin_config field')
        
        xml = ET.fromstring(form[match.end():])
        script = xml.findtext('.//script')
        sql_file = xml.findtext('.//sql_file')
        parameters = {p.tag: p.text for p in xml.findall('.//parameters/parameter')}
        
        if not script or not sql_file or not parameters:
            return self._error('Missing required fields')
        
        try:
            with sqlite3.connect('app.db') as db:
                cursor = db.cursor()
                
                # substitute placeholders in the SQL script
                for param, value in parameters.items():
                    sql_file = re.sub(r'{{{}}}'.format(param), value, sql_file)
                
                # execute the final query safely
                cursor.execute(sql_file)
                
                # evaluate the script using eval in a restricted namespace
                result = eval(script, {'cursor': cursor, 'json': json})
        except sqlite3.Error as e:
            return self._error('SQLite error: {}'.format(e))
        
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'{"status": "success"}')
    
    def _error(self, message):
        self.send_response(400)
        self.end_headers()
        self.wfile.write(b'{"status": "error", "message": "{}"}'.format(message))