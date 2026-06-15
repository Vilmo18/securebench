import http.server
import sqlite3
import hashlib
import secrets
import http.cookies
import html
import time
import json
import urllib.parse

class ProfileService(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=os.getcwd(), **kwargs)
        self.db = sqlite3.connect("users.db")
        self.cursor = self.db.cursor()
        self.salt_length = 16
        self.session_timeout = 30 * 60 # seconds
        self.session_map = {}

    def do_GET(self):
        if self.path == "/":
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(b"<html><body>Welcome to my home page!</body></html>")
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        if self.path == "/login":
            username = self.get_form_value("username")
            password = self.get_form_value("password")
            user_id, name, bio, role = self.authenticate_user(username, password)
            if not user_id:
                self.send_response(403)
                self.end_headers()
                return
            session_token = secrets.token_hex(16)
            self.session_map[session_token] = (user_id, name, bio, role)
            expires = time.time() + self.session_timeout
            cookie = http.cookies.SimpleCookie({"session_id": session_token})
            cookie["session_id"]["expires"] = time.strftime("%a, %d %b %Y %H:%M:%S GMT", time.gmtime(expires))
            cookie["session_id"]["path"] = "/"
            cookie["session_id"]["HttpOnly"] = True
            cookie["session_id"]["Secure"] = True
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b"{ \"status\": \"ok\" }")
        else:
            self.send_response(404)
            self.end_headers()

    def do_PUT(self):
        if self.path == "/profile":
            session_token = self.get_session_id()
            if not session_token:
                self.send_response(401)
                self.end_headers()
                return
            user_id, name, bio, role = self.get_user_profile(session_token)
            if not user_id:
                self.send_response(403)
                self.end_headers()
                return
            if role != "admin":
                self.send_response(403)
                self.end_headers()
                return
            bio = self.get_form_value("bio")
            self.update_user_profile(user_id, bio)
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b"{ \"status\": \"ok\" }")
        else:
            self.send_response(404)
            self.end_headers()

    def get_session_id(self):
        cookie = http.cookies.SimpleCookie(self.headers["cookie"])
        if "session_id" not in cookie:
            return None
        session_token = cookie["session_id"].value
        if session_token not in self.session_map:
            return None
        return session_token

    def get_user_profile(self, session_token):
        user_id, name, bio, role = self.session_map[session_token]
        return user_id, name, bio, role

    def authenticate_user(self, username, password):
        query = "SELECT id, name, bio, role FROM users WHERE username = ?"
        self.cursor.execute(query, (username,))
        row = self.cursor.fetchone()
        if not row:
            return None
        user_id, name, bio, role = row
        salt = secrets.token_hex(self.salt_length)
        hashed_password = hashlib.sha256((salt + password).encode()).hexdigest()
        query = "SELECT id FROM users WHERE username = ? AND password = ?"
        self.cursor.execute(query, (username, hashed_password))
        row = self.cursor.fetchone()
        if not row:
            return None
        user_id, = row
        return user_id, name, bio, role

    def update_user_profile(self, user_id, bio):
        query = "UPDATE users SET bio = ? WHERE id = ?"
        self.cursor.execute(query, (bio, user_id))
        self.db.commit()

    def get_form_value(self, name):
        return urllib.parse.unquote(self.rfile.read(int(self.headers["Content-Length"])).decode()).split("&")[0].split("=")[1]