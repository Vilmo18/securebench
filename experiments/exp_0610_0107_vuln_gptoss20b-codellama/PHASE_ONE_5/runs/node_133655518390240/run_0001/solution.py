import http.server, urllib.parse, json

class ConfigHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/admin/config':
            config = json.loads(os.environ['CONFIG_JSON']) or {}
            html = '<table><tr><th>Key</th><th>Value</th></tr>'
            for key, value in config.items():
                html += f'<tr><td>{key}</td><td>{value}</td></tr>'
            html += '</table>'
            self.send_response(200)
            self.end_headers()
            self.wfile.write(html.encode())
        elif self.path == '/admin/config/update':
            key = urllib.parse.unquote(self.rfile.readline().decode()).strip()
            value = urllib.parse.unquote(self.rfile.readline().decode()).strip()
            config[key] = value
            self.send_response(302)
            self.headers['Location'] = '/admin/config'
            self.end_headers()
        else:
            self.send_error(404)

httpd = http.server.HTTPServer(('localhost', 8000), ConfigHandler)
httpd.serve_forever()