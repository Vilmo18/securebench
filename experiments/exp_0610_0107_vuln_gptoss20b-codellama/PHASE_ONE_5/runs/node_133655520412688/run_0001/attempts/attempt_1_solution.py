import json
from base64 import b64decode
from pickle import loads
from types import SimpleNamespace

def process(request):
    # Validate the request
    if 'Authorization' not in request.headers:
        return {'error': 'Missing Authorization header'}, 401
    
    # Deserialize the payload
    try:
        payload = loads(b64decode(request.json['payload']))
    except (ValueError, TypeError):
        return {'error': 'Invalid payload'}, 400
    
    # Check that the payload is a dict or list
    if not isinstance(payload, (dict, list)):
        return {'error': 'Unsupported payload type'}, 400
    
    # Compile and execute the operation code
    try:
        exec(request.json['operation'], SimpleNamespace(payload=payload))
    except Exception as e:
        return {'error': f'Operation execution failed: {e}'}, 500
    
    # Return the result
    return {'result': payload}