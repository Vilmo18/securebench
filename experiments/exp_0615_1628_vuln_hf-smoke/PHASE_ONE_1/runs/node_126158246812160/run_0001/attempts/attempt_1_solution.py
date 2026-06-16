import json
import hashlib
import hmac
import base64
import time
import os

# Simulated user store with hashed passwords
USER_STORE = {
    "alice": hashlib.sha256(b"alice_password").hexdigest(),
    "bob": hashlib.sha256(b"bob_password").hexdigest(),
    "charlie": hashlib.sha256(b"charlie_password").hexdigest()
}

ALLOWED_ROLES = {"admin", "editor", "viewer"}

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(username, password_hash):
    return USER_STORE.get(username) == password_hash

def generate_jwt_token(username, role):
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {"sub": username, "role": role, "exp": int(time.time()) + 3600}
    secret_key = os.environ.get("JWT_SECRET_KEY", "").encode()

    def encode_section(section):
        return base64.urlsafe_b64encode(json.dumps(section).encode()).rstrip(b'=')

    encoded_header = encode_section(header)
    encoded_payload = encode_section(payload)
    signature = hmac.new(secret_key, encoded_header + b"." + encoded_payload, hashlib.sha256).digest()
    encoded_signature = base64.urlsafe_b64encode(signature).rstrip(b'=')

    return b".".join([encoded_header, encoded_payload, encoded_signature]).decode()

def login_handler(request_body):
    try:
        data = json.loads(request_body)
    except json.JSONDecodeError:
        return json.dumps({"error": "Invalid JSON"}), 400

    username = data.get("username")
    password = data.get("password")
    role = data.get("role", "viewer")

    if not isinstance(username, str) or not username:
        return json.dumps({"error": "Username is required"}), 400
    if not isinstance(password, str) or not password:
        return json.dumps({"error": "Password is required"}), 400
    if role not in ALLOWED_ROLES:
        return json.dumps({"error": "Invalid role"}), 400

    password_hash = hash_password(password)
    if not verify_password(username, password_hash):
        return json.dumps({"error": "Invalid credentials"}), 401

    token = generate_jwt_token(username, role)
    return json.dumps({"token": token}), 200

# Example usage
if __name__ == "__main__":
    request_body = '{"username": "alice", "password": "alice_password", "role": "admin"}'
    response, status_code = login_handler(request_body)
    print(response, status_code)