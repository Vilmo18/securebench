import base64
import json
from datetime import datetime, timedelta
from http import HTTPStatus

def validate_session_token(header):
    try:
        token = base64.b64decode(header).decode()
    except (UnicodeDecodeError, binascii.Error) as e:
        return False, "Invalid encoding"
    
    try:
        payload = json.loads(token)
    except json.JSONDecodeError as e:
        return False, "Malformed JSON"
    
    if not all(key in payload for key in ["user_id", "role", "expires_at"]):
        return False, "Missing required fields"
    
    expiration = datetime.fromisoformat(payload["expires_at"])
    if expiration < datetime.now():
        return False, "Expired token"
    
    if payload["role"] != "admin":
        return False, "Unauthorized access"
    
    return True, None

def handle_request(request):
    header = request.headers.get("X-Session-Token")
    if not header:
        return HTTPStatus.BAD_REQUEST, {"error": "Missing session token"}
    
    valid, reason = validate_session_token(header)
    if not valid:
        return HTTPStatus.UNAUTHORIZED, {"error": reason}
    
    # Return the protected data as a JSON response with appropriate status codes and content-type headers.
    return HTTPStatus.OK, {"data": "secure content"}