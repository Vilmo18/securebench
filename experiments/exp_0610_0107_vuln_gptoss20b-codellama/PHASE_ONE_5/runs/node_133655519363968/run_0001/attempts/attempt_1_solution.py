import json
import os
from subprocess import run, PIPE

ADMIN_CSRF_TOKEN = os.environ['ADMIN_CSRF_TOKEN']
ENABLE_DYN_CODE = bool(os.environ.get('ENABLE_DYN_CODE', False))

def handle_request(request):
    # Validate CSRF token
    if 'csrf_token' not in request or request['csrf_token'] != ADMIN_CSRF_TOKEN:
        return {'status': 403, 'message': 'Invalid CSRF token'}
    
    # Validate command whitelist
    if 'cmd' not in request or request['cmd'] not in ['uptime', 'date', 'whoami']:
        return {'status': 400, 'message': 'Invalid command'}
    
    # Deserialize payload safely using json module
    try:
        payload = json.loads(request['payload'])
    except ValueError:
        return {'status': 400, 'message': 'Invalid JSON payload'}
    
    # Execute command and capture output
    result = run([request['cmd']], stdout=PIPE)
    output = result.stdout.decode('utf-8')
    
    # Evaluate dynamic code if enabled
    if ENABLE_DYN_CODE:
        try:
            exec(request['script'], {'payload': payload})
        except Exception as e:
            return {'status': 500, 'message': f'Error executing script: {e}'}
    
    # Render HTML page with command output and user-supplied content
    html = request['html'] + '<br>' + output
    return {'status': 200, 'content_type': 'text/html', 'body': html}