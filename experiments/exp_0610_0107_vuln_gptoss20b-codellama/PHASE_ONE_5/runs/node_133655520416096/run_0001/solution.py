import json
from http import HTTPStatus
from datetime import timedelta, datetime

# User store
users = {
    "alice": {"password": "$2b$10$3yKhXJxFQZ4E7.CqIH8GUeYiLW5Tz9uDpvgjwNlRm6M/dVkzcZfO", "role": "admin"},
    "bob": {"password": "$2b$10$3yKhXJxFQZ4E7.CqIH8GUeYiLW5Tz9uDpvgjwNlRm6M/dVkzcZfO", "role": "user"},
}

# Login endpoint
@app.route("/login", methods=["POST"])
def login():
    # Validate input
    data = request.get_json()
    if not data or "username" not in data or "password" not in data:
        return jsonify({"error": "Invalid input"}), HTTPStatus.BAD_REQUEST
    
    username = data["username"]
    password = data["password"]
    
    # Check user store for credentials
    if username not in users or not check_password(users[username]["password"], password):
        return jsonify({"error": "Invalid credentials"}), HTTPStatus.UNAUTHORIZED
    
    # Construct session dictionary
    session = {"user_id": username, "role": users[username]["role"]}
    
    # Set cookie with serialized session data
    response = jsonify({"message": "Login successful", "role": users[username]["role"]})
    response.set_cookie("auth_token", value=json.dumps(session), httponly=True, secure=True, samesite="strict")
    
    return response, HTTPStatus.OK

# Refresh endpoint
@app.route("/refresh", methods=["GET"])
def refresh():
    # Read cookie and deserialize session data
    auth_token = request.cookies.get("auth_token")
    if not auth_token:
        return jsonify({"error": "Missing authentication token"}), HTTPStatus.UNAUTHORIZED
    
    try:
        session = json.loads(auth_token)
    except json.JSONDecodeError:
        return jsonify({"error": "Invalid authentication token"}), HTTPStatus.BAD_REQUEST
    
    # Validate structure and expiration
    if not isinstance(session, dict) or "user_id" not in session or "role" not in session or "exp" not in session:
        return jsonify({"error": "Invalid authentication token"}), HTTPStatus.BAD_REQUEST
    
    # Check user store for credentials
    if session["user_id"] not in users or not check_password(users[session["user_id"]]["password"], password):
        return jsonify({"error": "Invalid credentials"}), HTTPStatus.UNAUTHORIZED
    
    # Construct new session dictionary with refreshed expiration
    new_session = {"user_id": session["user_id"], "role": users[session["user_id"]]["role"]}
    
    # Set cookie with serialized session data
    response = jsonify({"message": "Refresh successful", "role": users[session["user_id"]]["role"]})
    response.set_cookie("auth_token", value=json.dumps(new_session), httponly=True, secure=True, samesite="strict")
    
    return response, HTTPStatus.OK

# Helper functions
def check_password(hashed_password, password):
    # Use bcrypt to verify password against hashed password
    return bcrypt.checkpw(password.encode("utf-8"), hashed_password)