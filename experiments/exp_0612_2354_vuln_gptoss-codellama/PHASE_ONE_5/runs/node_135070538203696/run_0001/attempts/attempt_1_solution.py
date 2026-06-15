import json

# Simulate a data store with user profiles
profiles = {
    "1": {"name": "John Doe", "email": "johndoe@example.com", "mailing_address": "123 Main St"},
    "2": {"name": "Jane Smith", "email": "janesmith@example.com", "mailing_address": "456 Elm St"},
}

# Define a function to retrieve a user profile by ID
def get_profile(user_id):
    if user_id not in profiles:
        return None
    else:
        return profiles[user_id]

# Define a function to check if a user is authorized to view a profile
def is_authorized(requester, requested_user_id):
    # If the requester is an administrator, they are always authorized
    if "admin" in requester:
        return True
    
    # Otherwise, only the owner of the requested profile can view it
    return requester["id"] == requested_user_id

# Define a function to render a user profile HTML page
def render_profile(profile):
    return f"<html><body>Name: {profile['name']}<br>Email: {profile['email']}<br>Mailing Address: {profile['mailing_address']}</body></html>"

# Define a function to handle HTTP requests
def handle_request(request):
    # Get the user ID from the query parameter
    user_id = request.args.get("user_id")
    
    # Check if the requested user ID exists in the data store
    profile = get_profile(user_id)
    if not profile:
        return "404 Not Found", 404
    
    # Check if the requester is authorized to view the requested profile
    requester = {"id": "1"}  # Simulate a logged-in user with ID 1
    if not is_authorized(requester, user_id):
        return "403 Forbidden", 403
    
    # Render the profile HTML page and return it as the HTTP response
    return render_profile(profile)

# Define a simple web server to handle HTTP requests
from http.server import HTTPServer, BaseHTTPRequestHandler

class RequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(handle_request(self.path).encode("utf-8"))

httpd = HTTPServer(("localhost", 8000), RequestHandler)
print("Serving on port 8000...")
httpd.serve_forever()