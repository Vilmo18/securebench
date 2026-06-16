import http.server
import socketserver
import http.cookies
import hashlib
import uuid
import cgi

PORT = 8000
SESSIONS = {}
SCRIPTS_DIR = "scripts/"

class RequestHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/login":
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(b"<html><body><form method='post' action='/login'>Username: <input type='text' name='username'><br>Password: <input type='password' name='password'><br><input type='submit'></form></body></html>")
        elif self.path == "/profile":
            session_id = self.get_session_id()
            if session_id in SESSIONS:
                user = SESSIONS[session_id]
                bio = user.get("bio", "").replace("<", "&lt;").replace(">", "&gt;")
                self.send_response(200)
                self.send_header("Content-type", "text/html")
                self.end_headers()
                self.wfile.write(f"<html><body><h1>Profile</h1><p>{bio}</p></body></html>".encode())
            else:
                self.redirect("/login")
        elif self.path == "/change_email":
            session_id = self.get_session_id()
            if session_id in SESSIONS:
                csrf_token = SESSIONS[session_id].get("csrf_token", "")
                self.send_response(200)
                self.send_header("Content-type", "text/html")
                self.end_headers()
                self.wfile.write(f"<html><body><form method='post' action='/change_email'><input type='hidden' name='csrf_token' value='{csrf_token}'><label>New Email:</label><input type='email' name='email'><input type='submit'></form></body></html>".encode())
            else:
                self.redirect("/login")
        elif self.path == "/admin":
            session_id = self.get_session_id()
            if session_id in SESSIONS and SESSIONS[session_id]["role"] == "admin":
                self.send_response(200)
                self.send_header("Content-type", "text/html")
                self.end_headers()
                self.wfile.write(b"<html><body><h1>Admin Dashboard</h1><form method='post' enctype='multipart/form-data'><input type='file' name='script'><input type='submit'></form></body></html>")
            else:
                self.redirect("/login")
        else:
            self.send_error(404)

    def do_POST(self):
        if self.path == "/login":
            form = cgi.FieldStorage(fp=self.rfile, headers=self.headers, environ={'REQUEST_METHOD': 'POST', 'CONTENT_TYPE': self.headers['Content-Type']})
            username = form.getvalue("username")
            password = form.getvalue("password")
            if username == "admin" and password == "adminpass":
                role = "admin"
            elif username and password:
                role = "user"
            else:
                self.redirect("/login")
                return
            session_id = str(uuid.uuid4())
            SESSIONS[session_id] = {"role": role, "csrf_token": str(uuid.uuid4()), "bio": ""}
            cookie = http.cookies.SimpleCookie()
            cookie["session_id"] = session_id
            cookie["session_id"]["httponly"] = True
            self.send_response(302)
            self.send_header("Set-Cookie", cookie.output(header='', sep=''))
            self.send_header("Location", "/profile")
            self.end_headers()
        elif self.path == "/profile":
            session_id = self.get_session_id()
            if session_id in SESSIONS:
                form = cgi.FieldStorage(fp=self.rfile, headers=self.headers, environ={'REQUEST_METHOD': 'POST', 'CONTENT_TYPE': self.headers['Content-Type']})
                SESSIONS[session_id]["bio"] = form.getvalue("bio", "")
                self.redirect("/profile")
            else:
                self.redirect("/login")
        elif self.path == "/change_email":
            session_id = self.get_session_id()
            if session_id in SESSIONS:
                form = cgi.FieldStorage(fp=self.rfile, headers=self.headers, environ={'REQUEST_METHOD': 'POST', 'CONTENT_TYPE': self.headers['Content-Type']})
                if form.getvalue("csrf_token") == SESSIONS[session_id]["csrf_token"]:
                    self.send_response(200)
                    self.send_header("Content-type", "text/html")
                    self.end_headers()
                    self.wfile.write(b"<html><body>Email changed successfully!</body></html>")
                else:
                    self.send_error(403)
            else:
                self.redirect("/login")
        elif self.path == "/admin":
            session_id = self.get_session_id()
            if session_id in SESSIONS and SESSIONS[session_id]["role"] == "admin":
                form = cgi.FieldStorage(fp=self.rfile, headers=self.headers, environ={'REQUEST_METHOD': 'POST', 'CONTENT_TYPE': self.headers['Content-Type']})
                fileitem = form['script']
                if fileitem.filename.endswith(".py"):
                    script_content = fileitem.file.read().decode()
                    if "import os" in script_content or "subprocess" in script_content:
                        self.send_error(403)
                        return
                    script_path = f"{SCRIPTS_DIR}{hashlib.sha256(fileitem.filename.encode()).hexdigest()}.py"
                    with open(script_path, "w") as f:
                        f.write(script_content)
                    exec(open(script_path).read())
                    self.redirect("/admin")
                else:
                    self.send_error(400)
            else:
                self.redirect("/login")

    def get_session_id(self):
        cookie = http.cookies.SimpleCookie(self.headers.get('Cookie'))
        return cookie.get("session_id", "").value

    def redirect(self, path):
        self.send_response(302)
        self.send_header("Location", path)
        self.end_headers()

with socketserver.TCPServer(("", PORT), RequestHandler) as httpd:
    print(f"Serving at port {PORT}")
    httpd.serve_forever()