import json
import xml.etree.ElementTree as ET
import uuid
import hashlib
import subprocess
import os

# Mock user database
users_db = {
    "admin": {"password": hashlib.pbkdf2_hmac('sha256', "adminpass".encode(), b'salt', 100000).hex(), "role": "admin"},
    "user": {"password": hashlib.pbkdf2_hmac('sha256', "userpass".encode(), b'salt', 100000).hex(), "role": "user"}
}

# Mock session store
sessions = {}

def authenticate(username, password):
    if username not in users_db:
        return False
    hashed_password = hashlib.pbkdf2_hmac('sha256', password.encode(), b'salt', 100000).hex()
    return users_db[username]["password"] == hashed_password

def generate_session_token(username):
    token = str(uuid.uuid4())
    sessions[token] = username
    return token

def parse_profile_xml(profile_xml):
    try:
        root = ET.fromstring(profile_xml)
        theme = root.find('theme').text if root.find('theme') is not None else None
        layout = root.find('layout').text if root.find('layout') is not None else None
        return {"theme": theme, "layout": layout}
    except ET.ParseError:
        raise ValueError("Invalid XML format")

def generate_report(report_type):
    try:
        result = subprocess.run([os.path.join('/usr/local/bin', 'generate_report'), "--type", report_type], capture_output=True, text=True)
        if result.returncode != 0:
            raise ValueError(f"Report generation failed: {result.stderr}")
        return result.stdout
    except Exception as e:
        raise ValueError(str(e))

def login_handler(request):
    try:
        data = json.loads(request["body"])
        username = data.get("username")
        password = data.get("password")

        if not username or not isinstance(username, str) or not password or not isinstance(password, str):
            return {"status": 400, "message": "Invalid input"}

        if not authenticate(username, password):
            return {"status": 401, "message": "Authentication failed"}

        session_token = generate_session_token(username)

        profile_xml = data.get("profile_xml")
        if profile_xml:
            preferences = parse_profile_xml(profile_xml)
            users_db[username].update(preferences)

        return {"status": 200, "session_token": session_token}
    except Exception as e:
        return {"status": 500, "message": str(e)}

def report_handler(request):
    try:
        session_token = request.get("headers", {}).get("Authorization")
        if not session_token or session_token not in sessions:
            return {"status": 401, "message": "Unauthorized"}

        username = sessions[session_token]
        user_role = users_db[username]["role"]

        report_type = request["query_params"].get("report_type")
        if not report_type:
            return {"status": 400, "message": "Missing report type"}

        if user_role != "admin":
            return {"status": 403, "message": "Forbidden"}

        report_output = generate_report(report_type)
        return {"status": 200, "report": report_output}
    except Exception as e:
        return {"status": 500, "message": str(e)}

# Example request handlers
def handle_request(request):
    if request["method"] == "POST" and request["path"] == "/login":
        return login_handler(request)
    elif request["method"] == "GET" and request["path"] == "/report":
        return report_handler(request)
    else:
        return {"status": 404, "message": "Not Found"}