import os
import json
from subprocess import run

BASE_DIR = '/app/configs/'

def handle_request(request):
    config_path = request.get('config_path', '')
    if not config_path:
        return json.dumps({'error': 'No config path provided'}), 400

    # Resolve the supplied path against the base directory
    full_path = os.path.abspath(os.path.join(BASE_DIR, config_path))

    # Ensure the final location is a regular file within that directory tree
    if not (full_path.startswith(BASE_DIR) and os.path.isfile(full_path)):
        return json.dumps({'error': 'Invalid or inaccessible configuration file'}), 403

    try:
        with open(full_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except (OSError, UnicodeDecodeError):
        return json.dumps({'error': 'Failed to read the configuration file'}), 500

    # Invoke the external script process_config.sh
    result = run(['/path/to/process_config.sh', full_path], capture_output=True, shell=False)
    if result.returncode != 0:
        return json.dumps({'error': f'Processing failed: {result.stderr.decode("utf-8")}'}), 500

    return json.dumps({'success': 'Configuration processed successfully'}), 200