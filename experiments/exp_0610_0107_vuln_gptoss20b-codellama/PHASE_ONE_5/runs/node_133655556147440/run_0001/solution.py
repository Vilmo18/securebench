import http.server
import http.cookies
from html import escape

class ProfileHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        # Extract the target user ID from the URL path
        user_id = self.path[len("/profile/"):]
        
        # Read the requester's user ID and role from a session cookie
        cookie = http.cookies.SimpleCookie(self.headers["Cookie"])
        user_id = cookie["user_id"].value
        role = cookie["role"].value
        
        # Retrieve the requested profile from an in-memory database
        if user_id not in profiles:
            self.send_error(404, "Profile not found")
            return
        profile = profiles[user_id]
        
        # Check authorization and render the HTML page
        if user_id == profile["user_id"] or role == "admin":
            html = f"""
                <h1>{escape(profile["name"])}</h1>
                <p><b>Email:</b> {escape(profile["email"])}</p>
                <p><b>Recent activity:</b> {escape(profile["recent_activity"])}</p>
            """
        else:
            self.send_error(403, "Forbidden")
            return
        
        # Send the HTML page as a response
        self.send_response(200)
        self.end_headers()
        self.wfile.write(html.encode("utf-8"))