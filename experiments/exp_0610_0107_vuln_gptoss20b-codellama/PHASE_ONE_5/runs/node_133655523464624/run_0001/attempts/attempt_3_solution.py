import json
from base64 import b64decode
from pickle import loads

def upload_config(request):
    # Verify that the request body is valid JSON and contains the required key
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return HttpResponseBadRequest('Invalid JSON')
    if 'config_blob' not in data:
        return HttpResponseBadRequest('Missing config_blob field')
    
    # Decode the base64 value to bytes and verify its size
    try:
        config_bytes = b64decode(data['config_blob'])
    except binascii.Error:
        return HttpResponseBadRequest('Invalid base64 encoding')
    if len(config_bytes) > 65536:
        return HttpResponseBadRequest('Config blob exceeds maximum size of 64 KiB')
    
    # Load the decoded bytes using pickle.loads and verify that it is a dictionary
    try:
        config = loads(config_bytes)
    except Exception as e:
        return HttpResponseBadRequest(f'Error loading config blob: {e}')
    if not isinstance(config, dict):
        return HttpResponseBadRequest('Config blob must be a dictionary')
    
    # Ensure the dictionary contains only the allowed keys and verify their values
    allowed_keys = {'timeout', 'max_connections', 'enable_logging'}
    for key in config.keys():
        if key not in allowed_keys:
            return HttpResponseBadRequest(f'Invalid configuration key {key}')
    
    # Apply the validated settings to the application's in-memory configuration module
    # ...
    
    return HttpResponse('{"status": "success"}', content_type='application/json')