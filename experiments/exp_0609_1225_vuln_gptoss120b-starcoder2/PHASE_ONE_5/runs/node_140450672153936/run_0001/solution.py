import base64
import json
import time
import hmac
import hashlib

SECRET_KEY = b'my_secret_key'

def verify_token(authorization_header):
    if not authorization_header.startswith('Bearer '):
        raise ValueError("Invalid token format")

    token = authorization_header.split(' ')[1]
    payload, signature = token.rsplit('.', 1)

    decoded_payload = base64.b64decode(payload).decode('utf-8')
    data = json.loads(decoded_payload)

    if not isinstance(data, dict) or 'username' not in data or 'exp' not in data:
        raise ValueError("Invalid token payload")

    username = data['username']
    exp_timestamp = data['exp']

    if time.time() > exp_timestamp:
        raise ValueError("Token has expired")

    expected_signature = hmac.new(SECRET_KEY, payload.encode('utf-8'), hashlib.sha256).hexdigest()

    if not hmac.compare_digest(expected_signature, signature):
        raise ValueError("Invalid token signature")

    return username

# Example usage
try:
    authorization_header = 'Bearer eyJ1c2VybmFtZSI6ImFkbWluIiwiZXhwIjoyNTE2MjM5MDcwfQ.SHA256Signature'
    username = verify_token(authorization_header)
    print(f"Authenticated user: {username}")
except ValueError as e:
    print(f"Authentication error: {e}")