import json
import re
import subprocess
import sys

def validate_image(image):
    return bool(re.match(r'^[a-zA-Z0-9._:-]+$', image))

def validate_env_var(name):
    return bool(re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', name))

def main(json_file_path):
    try:
        with open(json_file_path, 'r') as file:
            config = json.load(file)

        image = config.get('image')
        env_vars = config.get('env', {})

        if not image or not validate_image(image):
            raise ValueError("Invalid image name")

        for name in env_vars:
            if not validate_env_var(name):
                raise ValueError(f"Invalid environment variable name: {name}")

        cmd = ['docker', 'run', '-d']
        for name, value in env_vars.items():
            cmd.extend(['-e', f'{name}={value}'])
        cmd.append(image)

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"Error: {result.stderr}")
            sys.exit(1)

        print(f"Container started with ID: {result.stdout.strip()}")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: start_container.py <path_to_json_file>")
        sys.exit(1)
    main(sys.argv[1])