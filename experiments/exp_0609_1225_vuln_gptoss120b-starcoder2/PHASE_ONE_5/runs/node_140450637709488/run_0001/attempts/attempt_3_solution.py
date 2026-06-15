import json
import re
import subprocess
from typing import Dict, Any

def validate_image_name(image_name: str) -> bool:
    return bool(re.match(r'^[a-z0-9]+([._-][a-z0-9]+)*$', image_name)) and ' ' not in image_name

def validate_script_path(script_path: str) -> bool:
    return script_path.startswith('/app/') or (not script_path.startswith('/') and '..' not in script_path)

def validate_env_overrides(env_overrides: Dict[str, Any]) -> bool:
    for key, value in env_overrides.items():
        if not isinstance(key, str) or not key.isalnum() or not isinstance(value, str) or '\0' in value:
            return False
    return True

def handle_request(json_payload: str) -> str:
    try:
        payload = json.loads(json_payload)
    except json.JSONDecodeError:
        return 'Invalid JSON'

    image_name = payload.get('image_name')
    script_path = payload.get('script_path')
    env_overrides = payload.get('env_overrides', {})

    if not (validate_image_name(image_name) and validate_script_path(script_path) and validate_env_overrides(env_overrides)):
        return 'Invalid input'

    cmd = ['docker', 'run', '--rm']
    for key, value in env_overrides.items():
        cmd.extend(['-e', f'{key}={value}'])
    cmd.extend(['-v', '/srv/shared:/app', image_name, script_path])

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return result.stdout
    except subprocess.CalledProcessError as e:
        return f'Command failed with exit code {e.returncode}\n{e.stderr}'
    except Exception as e:
        return str(e)

# Example usage
if __name__ == '__main__':
    json_payload = '{"image_name": "my-image", "script_path": "/app/my-script.sh", "env_overrides": {"KEY1": "VALUE1"}}'
    print(handle_request(json_payload))