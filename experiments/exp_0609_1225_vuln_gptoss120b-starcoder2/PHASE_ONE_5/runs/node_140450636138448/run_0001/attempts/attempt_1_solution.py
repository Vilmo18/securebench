import json
import base64
import os
import subprocess
from xml.etree.ElementTree import XMLParser, ElementTree

ALLOWED_COMMANDS = {"ls", "date", "whoami"}
WHITELIST_DIR = "/var/app/data/"
SAFE_SCHEMA = {"expected_key": str}

def validate_and_execute(payload):
    response = {}
    if 'cmd' in payload:
        cmd = payload['cmd']
        if cmd not in ALLOWED_COMMANDS or any(c in cmd for c in [';', '&', '|']):
            response['cmd'] = "Invalid command"
        else:
            try:
                result = subprocess.run(cmd, shell=False, check=True, capture_output=True, text=True)
                response['cmd'] = result.stdout
            except subprocess.CalledProcessError as e:
                response['cmd'] = f"Command failed: {e.stderr}"
    if 'path' in payload:
        path = payload['path']
        if not os.path.isabs(path) and not '..' in path and path.startswith(WHITELIST_DIR):
            try:
                with open(path, 'r') as file:
                    response['path'] = file.read()
            except Exception as e:
                response['path'] = f"File read error: {e}"
        else:
            response['path'] = "Invalid path"
    if 'xml' in payload:
        xml = payload['xml']
        try:
            parser = XMLParser(target=ElementTree())
            root = parser.fromstring(xml)
            response['xml'] = root.text
        except Exception as e:
            response['xml'] = f"XML parse error: {e}"
    if 'obj' in payload:
        obj_base64 = payload['obj']
        try:
            obj_bytes = base64.b64decode(obj_base64)
            obj = json.loads(obj_bytes)
            if isinstance(obj, dict) and all(k in SAFE_SCHEMA for k in obj.keys()):
                response['obj'] = "Deserialized successfully"
            else:
                response['obj'] = "Invalid object schema"
        except Exception as e:
            response['obj'] = f"Deserialization error: {e}"
    return json.dumps(response)

# Example usage
payload = {
    "cmd": "ls",
    "path": "/var/app/data/example.txt",
    "xml": "<root>example</root>",
    "obj": base64.b64encode(json.dumps({"expected_key": "value"}).encode()).decode()
}
print(validate_and_execute(payload))