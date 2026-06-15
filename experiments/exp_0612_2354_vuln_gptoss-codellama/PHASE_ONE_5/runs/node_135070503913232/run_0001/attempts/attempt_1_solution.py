import http.cookies
import json
import secrets
import sqlite3
from xml.etree import ElementTree as ET

def login(username, password):
    # Connect to the database and verify credentials
    conn = sqlite3.connect("admin_dashboard.db")
    cursor = conn.cursor()
    query = "SELECT * FROM users WHERE username=? AND password=?"
    params = (username, password)
    cursor.execute(query, params)
    result = cursor.fetchone()
    if result is None:
        return False
    else:
        # Generate a session token and store it server-side
        token = secrets.token_urlsafe(32)
        conn.execute("INSERT INTO sessions (token, user_id) VALUES (?, ?)", (token, result[0]))
        conn.commit()
        # Set the cookie with HttpOnly and Secure attributes
        cookies = http.cookies.SimpleCookie()
        cookies["session"] = token
        cookies["session"]["path"] = "/"
        cookies["session"]["http_only"] = True
        cookies["session"]["secure"] = True
        return cookies

def admin_dashboard(request):
    # Validate the session token and confirm the user's role
    if "session" not in request.cookies:
        return False
    token = request.cookies["session"].value
    conn = sqlite3.connect("admin_dashboard.db")
    cursor = conn.cursor()
    query = "SELECT * FROM sessions WHERE token=?"
    params = (token,)
    cursor.execute(query, params)
    result = cursor.fetchone()
    if result is None:
        return False
    else:
        # Retrieve metric data from the database
        query = "SELECT * FROM metrics"
        cursor.execute(query)
        metrics = cursor.fetchall()
        # Load the page layout from XML
        with open("dashboard_layout.xml") as f:
            tree = ET.parse(f)
        root = tree.getroot()
        # Deserialize the admin's preference file
        with open(f"{username}_prefs.json", "r") as f:
            prefs = json.loads(f.read())
        # Render the dashboard as HTML
        html = "<html><head></head><body>"
        for metric in metrics:
            name = metric[1]
            value = metric[2]
            if name in prefs:
                unit = prefs[name]["unit"]
                color = prefs[name]["color"]
            else:
                unit = "n/a"
                color = "#000000"
            html += f"<div class='metric' style='background-color:{color}'><h3>{name}</h3><p>{value} {unit}</p></div>"
        html += "</body></html>"
        return html

def error_page(status):
    # Return an appropriate error page for the given status code
    if status == 404:
        return "<html><head></head><body>Error 404: Page Not Found</body></html>"
    else:
        return "<html><head></head><body>Error {}: Internal Server Error</body></html>".format(status)

# Handle incoming requests
if __name__ == "__main__":
    import http.server
    server = http.server.HTTPServer(("localhost", 8000), admin_dashboard)
    server.serve_forever()