import http.server
import socketserver
import tempfile
import subprocess
import json
import os
import shlex

class RequestHandler(http.server.BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path == '/run':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            try:
                data = json.loads(post_data)
                script_content = data.get('script', '')
                command_content = data.get('command', '')

                with tempfile.NamedTemporaryFile(delete=False, mode='w+t', suffix='.py') as temp_script:
                    temp_script.write(script_content)
                    temp_script_path = temp_script.name

                # Execute the Python script
                script_process = subprocess.Popen([shutil.which('python'), temp_script_path], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                script_stdout, script_stderr = script_process.communicate()

                # Execute the shell command
                command_args = shlex.split(command_content)
                command_process = subprocess.Popen(command_args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                command_stdout, command_stderr = command_process.communicate()

                # Clean up the temporary file
                os.unlink(temp_script_path)

                response = {
                    'script_output': script_stdout.decode('utf-8'),
                    'command_output': command_stdout.decode('utf-8')
                }

                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(response).encode('utf-8'))

            except Exception as e:
                self.send_response(500)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'error': str(e)}).encode('utf-8'))
        else:
            self.send_response(404)
            self.end_headers()

def run(server_class=http.server.HTTPServer, handler_class=RequestHandler, port=8000):
    server_address = ('', port)
    httpd = server_class(server_address, handler_class)
    httpd.serve_forever()

if __name__ == '__main__':
    run()