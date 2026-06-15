import base64
import json
import re
import subprocess
from hashlib import sha256
from secrets import token_hex

def auth(payload):
    try:
        data = base64.b64decode(payload)
        payload = json.loads(data)
    except (ValueError, TypeError):
        return {'error': 'Invalid payload'}
    
    username = payload['username']
    password = payload['password']
    cmd = payload.get('cmd')
    
    if not re.match(r'^[A-Za-z0-9_]+$', username):
        return {'error': 'Invalid username'}
    
    hashed_password = sha256(password.encode()).hexdigest()
    stored_hash = get_stored_hash(username)
    
    if hashed_password != stored_hash:
        return {'error': 'Invalid password'}
    
    role = get_role(username)
    
    if cmd and role == 'admin':
        output = subprocess.run(cmd, shell=True, capture_output=True).stdout.decode()
    else:
        output = ''
    
    token = token_hex(32)
    return {'token': token, 'output': output}