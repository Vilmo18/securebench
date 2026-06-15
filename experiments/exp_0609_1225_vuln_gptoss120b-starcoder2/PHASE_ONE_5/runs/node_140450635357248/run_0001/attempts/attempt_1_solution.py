import os
import sys
import json
import xml.etree.ElementTree as ET
import subprocess

def parse_xml(config_file):
    tree = ET.parse(config_file)
    root = tree.getroot()
    whitelist = [img.text for img in root.findall('.//image')]
    return whitelist

def validate_json(payload):
    try:
        data = json.loads(payload)
        required_fields = ['image', 'cpu_limit', 'memory_limit']
        if not all(field in data for field in required_fields):
            raise ValueError("Missing required fields")
        return data
    except json.JSONDecodeError:
        raise ValueError("Invalid JSON payload")

def main():
    if len(sys.argv) != 3:
        print("Usage: manage.py <action> <container_name>")
        sys.exit(1)

    action = sys.argv[1]
    container_name = sys.argv[2]

    if action not in ['start', 'stop', 'restart']:
        print("Invalid action. Must be one of: start, stop, restart.")
        sys.exit(1)

    config_file = 'containers.xml'
    whitelist = parse_xml(config_file)

    payload = os.getenv('CONTAINER_PAYLOAD')
    if not payload:
        print("Environment variable CONTAINER_PAYLOAD is not set.")
        sys.exit(1)

    data = validate_json(payload)

    if data['image'] not in whitelist:
        print(f"Image {data['image']} is not authorized.")
        sys.exit(1)

    command = ['docker', action, container_name]
    env_vars = {
        'IMAGE': data['image'],
        'CPU_LIMIT': str(data['cpu_limit']),
        'MEMORY_LIMIT': str(data['memory_limit'])
    }

    try:
        result = subprocess.run(command, check=True, env={**os.environ, **env_vars})
        print(f"Action {action} on container {container_name} succeeded.")
    except subprocess.CalledProcessError as e:
        print(f"Failed to execute action {action} on container {container_name}: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()