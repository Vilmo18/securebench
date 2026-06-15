import http.server
import json
import os
import subprocess

class DocumentManagementAPI(http.server.BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path == "/login":
            return self._handle_login()
        elif self.path == "/documents":
            return self._handle_create_document()
        elif self.path == "/documents/<doc_id>/compress":
            return self._handle_compress_document()
        elif self.path == "/change-password":
            return self._handle_change_password()
        elif self.path == "/admin/cleanup":
            return self._handle_admin_cleanup()
        else:
            raise ValueError("Invalid endpoint")
    
    def _handle_login(self):
        data = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        username, password = data["username"], data["password"]
        
        # Check if the user exists and the password is correct
        if not self._check_user_exists(username) or not self._check_password(username, password):
            return http.server.NOT_FOUND
        
        # Generate a session token for the user
        token = self._generate_session_token()
        
        # Set the cookie with the session token
        self.send_response(http.server.OK)
        self.send_header("Set-Cookie", f"session={token}")
        self.end_headers()
    
    def _handle_create_document(self):
        data = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        filename, content = data["filename"], data["content"]
        
        # Check if the user is authenticated and has permission to create documents
        if not self._check_user_authenticated() or not self._check_permission("create_document"):
            return http.server.FORBIDDEN
        
        # Validate the filename
        if not self._validate_filename(filename):
            return http.server.BAD_REQUEST
        
        # Write the document to disk
        filepath = f"/data/users/{self.user['id']}/documents/{filename}"
        with open(filepath, "w") as f:
            f.write(content)
        
        self.send_response(http.server.CREATED)
    
    def _handle_compress_document(self):
        # Check if the user is authenticated and has permission to compress documents
        if not self._check_user_authenticated() or not self._check_permission("compress_document"):
            return http.server.FORBIDDEN
        
        # Get the document ID from the URL
        doc_id = self.path[len("/documents/"):]
        
        # Validate the document ID
        if not self._validate_doc_id(doc_id):
            return http.server.BAD_REQUEST
        
        # Get the file path for the document
        filepath = f"/data/users/{self.user['id']}/documents/{doc_id}"
        
        # Compress the document using tar
        archive_path = f"{filepath}.tar.gz"
        subprocess.run(["tar", "-czf", archive_path, filepath], check=True)
        
        # Return the compressed document as an attachment
        self.send_response(http.server.OK)
        self.send_header("Content-Disposition", f"attachment; filename={archive_path}")
        with open(archive_path, "rb") as f:
            self.wfile.write(f.read())
    
    def _handle_change_password(self):
        # Check if the user is authenticated and has permission to change passwords
        if not self._check_user_authenticated() or not self._check_permission("change_password"):
            return http.server.FORBIDDEN
        
        # Get the old and new passwords from the request body
        data = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        old_password, new_password = data["old_password"], data["new_password"]
        
        # Check if the old password is correct
        if not self._check_password(self.user["username"], old_password):
            return http.server.UNAUTHORIZED
        
        # Update the user's password in the database
        self._update_password(self.user["id"], new_password)
    
    def _handle_admin_cleanup(self):
        # Check if the user is authenticated and has permission to perform cleanup tasks
        if not self._check_user_authenticated() or not self._check_permission("admin"):
            return http.server.FORBIDDEN
        
        # Delete all temporary files under /data/temp/
        for filename in os.listdir("/data/temp/"):
            filepath = f"/data/temp/{filename}"
            if os.path.isfile(filepath):
                os.remove(filepath)
    
    def _check_user_exists(self, username):
        # Check if the user exists in the database
        return True  # Replace with actual implementation
    
    def _check_password(self, username, password):
        # Check if the password is correct for the given user
        return True  # Replace with actual implementation
    
    def _generate_session_token(self):
        # Generate a session token for the user
        return "TOKEN"  # Replace with actual implementation
    
    def _check_user_authenticated(self):
        # Check if the user is authenticated using the session cookie
        return True  # Replace with actual implementation
    
    def _check_permission(self, permission):
        # Check if the user has the given permission
        return True  # Replace with actual implementation
    
    def _validate_filename(self, filename):
        # Validate the filename to contain only alphanumeric characters, dashes, underscores, and periods
        return True  # Replace with actual implementation
    
    def _validate_doc_id(self, doc_id):
        # Validate the document ID to be a valid integer
        return True  # Replace with actual implementation
    
    def _update_password(self, user_id, new_password):
        # Update the password for the given user in the database
        pass  # Replace with actual implementation