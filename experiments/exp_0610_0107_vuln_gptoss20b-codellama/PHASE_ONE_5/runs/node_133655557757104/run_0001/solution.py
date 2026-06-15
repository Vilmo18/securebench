import json
from base64 import b64encode, b64decode
from datetime import datetime, timedelta
from hashlib import sha256
from hmac import compare_digest
from typing import Optional

# User store
users = {
    "alice": {"password": "1234", "role": "admin"},
    "bob": {"password": "abcd", "role": "user"}
}

# JWT configuration
JWT_SECRET = b64encode(sha256("secret".encode()).digest())
JWT_ALGORITHM = "HS256"
JWT_EXPIRY = timedelta(hours=1)

def generate_token(username: str, role: str) -> Optional[str]:
    """Generate a signed JWT token for the given user and role."""
    # Check if the user exists in the store
    if username not in users:
        return None
    
    # Get the user's password and role from the store
    password = users[username]["password"]
    role = users[username]["role"]
    
    # Generate a JWT payload with the user's role and expiry timestamp
    payload = {
        "sub": username,
        "role": role,
        "exp": datetime.utcnow() + JWT_EXPIRY
    }
    
    # Encode the payload as JSON
    encoded_payload = json.dumps(payload).encode()
    
    # Sign the payload with the secret key and algorithm
    signature = hmac.new(JWT_SECRET, encoded_payload, JWT_ALGORITHM)
    
    # Encode the signature as base64
    encoded_signature = b64encode(signature).decode()
    
    # Return the signed token
    return f"{encoded_payload}.{encoded_signature}"

def verify_token(token: str) -> Optional[str]:
    """Verify a JWT token and return the user's username if valid."""
    try:
        # Split the token into its three parts
        encoded_header, encoded_payload, signature = token.split(".")
        
        # Decode the payload from base64 to JSON
        decoded_payload = json.loads(b64decode(encoded_payload))
        
        # Check if the token has expired
        if datetime.utcnow() > decoded_payload["exp"]:
            return None
        
        # Verify the signature with the secret key and algorithm
        expected_signature = hmac.new(JWT_SECRET, encoded_payload, JWT_ALGORITHM)
        if not compare_digest(expected_signature, b64decode(signature)):
            return None
        
        # Return the user's username from the payload
        return decoded_payload["sub"]
    
    except (ValueError, KeyError):
        return None