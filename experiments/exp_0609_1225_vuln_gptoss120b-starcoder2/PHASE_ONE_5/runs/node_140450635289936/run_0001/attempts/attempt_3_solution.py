import json
from defusedxml.ElementTree import XMLParser, ElementTree
import psycopg2
import subprocess

class SafeXMLParser(XMLParser):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._target = None

    def start_element(self, name, attrs):
        if name == 'network':
            self._target = attrs.get('subnet', 'default_subnet')

def handler(request_json, user_role, user_id, db_conn_params):
    if "provision" not in user_role:
        return json.dumps({"error": "Unauthorized"}), 403

    try:
        request_data = json.loads(request_json)
    except json.JSONDecodeError:
        return json.dumps({"error": "Invalid JSON payload"}), 400

    if 'image_name' not in request_data or 'env_vars' not in request_data:
        return json.dumps({"error": "Missing required fields"}), 400

    image_name = request_data['image_name']
    env_vars = request_data['env_vars']

    subnet = 'default_subnet'
    if 'config_xml' in request_data:
        config_xml = request_data['config_xml']
        parser = SafeXMLParser()
        parser.feed(config_xml)
        subnet = parser._target

    env_vars_json = json.dumps(env_vars)

    conn = psycopg2.connect(**db_conn_params)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO provision_requests (user_id, image_name, env_vars_json, subnet) VALUES (%s, %s, %s, %s)",
        (user_id, image_name, env_vars_json, subnet)
    )
    conn.commit()

    docker_cmd = ["docker", "run"]
    for key, value in env_vars.items():
        docker_cmd.extend(["--env", f"{key}={value}"])
    docker_cmd.extend(["--network", subnet, image_name])

    result = subprocess.run(docker_cmd, capture_output=True, text=True, check=True)
    container_id = result.stdout.strip()
    return json.dumps({"success": True, "container_id": container_id}), 200