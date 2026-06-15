import http.server
import sqlite3
import xml.etree.ElementTree as ET
import json
import base64

class ConfigUpdateHandler(http.server.BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path != '/api/config':
            return
        
        # Decode the bearer token and check the role
        auth = self.headers['Authorization']
        if not auth or not auth.startswith('Bearer '):
            self.send_response(403)
            self.end_headers()
            return
        
        token = auth[7:]
        try:
            data = base64.b64decode(token).decode('utf-8')
            user_id, role = json.loads(data)['user_id'], json.loads(data)['role']
        except (ValueError, KeyError):
            self.send_response(403)
            self.end_headers()
            return
        
        if role != 'admin':
            self.send_response(403)
            self.end_headers()
            return
        
        # Parse the XML payload and check for required elements
        try:
            xml = ET.fromstring(self.rfile.read())
        except ET.ParseError:
            self.send_response(400)
            self.end_headers()
            return
        
        entries = []
        for entry in xml.findall('entry'):
            key, value = entry.findtext('key'), entry.findtext('value')
            if not (key and value):
                self.send_response(400)
                self.end_headers()
                return
            
            entries.append((key, value))
        
        # Insert or update the configuration entries in the database
        conn = sqlite3.connect(':memory:')
        cur = conn.cursor()
        for key, value in entries:
            cur.execute("INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)", (key, value))
        
        # Return a JSON response with the updated keys
        self.send_response(200)
        self.end_headers()
        self.wfile.write(json.dumps({'updated_keys': [entry[0] for entry in entries]}))