import cgi
import html
import http.server
import secrets
import sqlite3
import xml.etree.ElementTree as ET
from hashlib import sha256
from http.cookies import SimpleCookie

class User:
    def __init__(self, username, password_hash, display_name, role):
        self.username = username
        self.password_hash = password_hash
        self.display_name = display_name
        self.role = role

class Role:
    def __init__(self, name, permissions):
        self.name = name
        self.permissions = permissions

class Permission:
    def __init__(self, resource, action):
        self.resource = resource
        self.action = action

def parse_xml(data):
    tree = ET.fromstring(data)
    root = tree.getroot()
    if root.tag != "roles":
        raise ValueError("Invalid XML root element")
    roles = {}
    for role in root:
        name = role.attrib["name"]
        permissions = []
        for permission in role:
            resource = permission.attrib["resource"]
            action = permission.attrib["action"]
            permissions.append(Permission(resource, action))
        roles[name] = Role(name, permissions)
    return roles

def validate_user(username, password):
    with sqlite3.connect("users.db") as conn:
        c = conn.cursor()
        hashed_password = sha256(password.encode()).hexdigest()
        c.execute("SELECT * FROM users WHERE username=? AND password_hash=?", (username, hashed_password))
        user = c.fetchone()
        if user is None:
            return None
        return User(*user)

def validate_role(user, role):
    with sqlite3.connect("users.db") as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM roles WHERE name=?", (role,))
        role_data = c.fetchone()
        if role_data is None:
            return False
        role = Role(*role_data)
        for permission in user.permissions:
            if permission.resource == role.name and permission.action == "read":
                return True
    return False

def generate_session_token():
    return secrets.token_hex(32)

def get_user_from_cookie(cookie):
    with sqlite3.connect("users.db") as conn:
        c = conn.cursor()
        token = cookie.value
        c.execute("SELECT * FROM sessions WHERE token=?", (token,))
        session = c.fetchone()
        if session is None:
            return None
        user_id = session[1]
        c.execute("SELECT * FROM users WHERE id=?", (user_id,))
        user = c.fetchone()
        if user is None:
            return None
        return User(*user)

def get_role_from_cookie(cookie):
    with sqlite3.connect("users.db") as conn:
        c = conn.cursor()
        token = cookie.value
        c.execute("SELECT * FROM sessions WHERE token=?", (token,))
        session = c.fetchone()
        if session is None:
            return None
        user_id = session[1]
        c.execute("SELECT * FROM roles WHERE id=?", (user_id,))
        role = c.fetchone()
        if role is None:
            return None
        return Role(*role)

def get_permissions(role):
    with sqlite3.connect("users.db") as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM permissions WHERE role=?", (role,))
        permissions = c.fetchall()
        return [Permission(*permission) for permission in permissions]

def handle_login(request):
    username = request.form["username"]
    password = request.form["password"]
    user = validate_user(username, password)
    if user is None:
        return "Invalid credentials", 401
    token = generate_session_token()
    with sqlite3.connect("users.db") as conn:
        c = conn.cursor()
        c.execute("INSERT INTO sessions (token, user) VALUES (?, ?)", (token, user.id))
        conn.commit()
    cookie = SimpleCookie(f"{token}; HttpOnly; SameSite=Strict")
    return f"Set-Cookie: {cookie}", 200

def handle_profile(request):
    cookie = request.cookies.get("session")
    if cookie is None:
        return "Unauthorized", 401
    user = get_user_from_cookie(cookie)
    if user is None:
        return "Invalid session token", 403
    display_name = html.escape(user.display_name)
    return f"<html><body>Hello, {display_name}!</body></html>", 200

def handle_admin(request):
    cookie = request.cookies.get("session")
    if cookie is None:
        return "Unauthorized", 401
    user = get_user_from_cookie(cookie)
    if user is None:
        return "Invalid session token", 403
    role = get_role_from_cookie(cookie)
    if not validate_role(user, role):
        return "Forbidden", 403
    with sqlite3.connect("users.db") as conn:
        c = conn.cursor()
        xml = request.files["xml"][0]
        try:
            roles = parse_xml(xml)
            for role in roles:
                name = role.name
                permissions = [permission.resource + "," + permission.action for permission in role.permissions]
                c.execute("INSERT INTO roles (name, permissions) VALUES (?, ?)", (name, ",".join(permissions)))
            conn.commit()
        except ValueError as e:
            return "Invalid XML", 400
    return "OK", 200

def handle_request(request):
    if request.method == "POST" and request.path == "/login":
        return handle_login(request)
    elif request.method == "GET" and request.path == "/profile":
        return handle_profile(request)
    elif request.method == "POST" and request.path == "/admin/upload_roles":
        return handle_admin(request)
    else:
        return "Not Found", 404

if __name__ == "__main__":
    http.server.test(handle_request, port=8000)