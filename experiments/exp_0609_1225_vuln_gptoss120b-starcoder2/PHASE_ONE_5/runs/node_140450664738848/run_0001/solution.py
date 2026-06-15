import os
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
import importlib.util

PLUGINS_DIR = '/opt/app/plugins'

def load_plugin(plugin_name):
    if not all(c.isalnum() or c == '_' for c in plugin_name):
        return {"error": "Invalid plugin name"}, 400

    plugin_path = os.path.join(PLUGINS_DIR, f"{plugin_name}.py")

    # Use realpath and abspath to prevent path traversal
    resolved_path = os.path.abspath(os.path.realpath(plugin_path))
    if not resolved_path.startswith(os.path.abspath(PLUGINS_DIR)):
        return {"error": "Invalid plugin path"}, 400

    if not os.path.exists(resolved_path):
        return {"error": "Plugin file does not exist"}, 400

    spec = importlib.util.spec_from_file_location(plugin_name, resolved_path)
    if spec is None:
        return {"error": "Failed to load plugin module"}, 400

    module = importlib.util.module_from_spec(spec)

    try:
        spec.loader.exec_module(module)
    except Exception as e:
        return {"error": f"Error loading plugin: {str(e)}"}, 400

    if not hasattr(module, 'run'):
        return {"error": "Plugin does not have a run() function"}, 400

    try:
        result = module.run()
    except Exception as e:
        return {"error": f"Error executing plugin: {str(e)}"}, 400

    return json.dumps(result), 200

class RequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path.startswith('/export?'):
            query = self.path.split('?')[1]
            params = dict(qc.split('=') for qc in query.split('&'))
            plugin_name = params.get('plugin_name')

            if not plugin_name:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(json.dumps({"error": "Missing plugin_name parameter"}).encode())
                return

            response, status_code = load_plugin(plugin_name)

            self.send_response(status_code)
            self.end_headers()
            self.wfile.write(response.encode())

def run(server_class=HTTPServer, handler_class=RequestHandler):
    server_address = ('', 8000)
    httpd = server_class(server_address, handler_class)
    print('Starting httpd server on port 8000...')
    httpd.serve_forever()

if __name__ == '__main__':
    run()