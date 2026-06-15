import os
import json
import re
import subprocess

def main():
    config_path = os.getenv('CONFIG_PATH')
    if not config_path:
        raise Exception("CONFIG_PATH environment variable is not set")

    # Ensure the path is relative and within /etc/container_configs/
    base_dir = '/etc/container_configs/'
    if not config_path.startswith(base_dir):
        raise Exception(f"Invalid configuration file path: {config_path}")

    resolved_path = os.path.normpath(os.path.join(base_dir, config_path))
    if not resolved_path.startswith(base_dir) or '..' in resolved_path.split('/'):
        raise Exception("Path traversal attempt detected")

    with open(resolved_path, 'r') as f:
        config = json.load(f)

    image = config.get('image')
    cmd = config.get('cmd', [])

    if not isinstance(image, str) or not re.match(r'^[a-z0-9]+(/[a-z0-9]+)*(:[a-z0-9._-]+)?$', image):
        raise Exception("Invalid Docker image name")

    if cmd and not all(isinstance(arg, str) and ';' not in arg and '&' not in arg for arg in cmd):
        raise Exception("Invalid command arguments")

    docker_cmd = ['docker', 'run']
    docker_cmd.append(image)
    docker_cmd.extend(cmd)

    subprocess.run(docker_cmd, check=True)

    print(f"Successfully launched container with image {image} and command {cmd}")

if __name__ == "__main__":
    main()