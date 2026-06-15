import http.server
import pickle
import hashlib
import subprocess

class LoginHandler(http.server.BaseHTTPRequestHandler):
    def do_POST(self):
        username = self.headers['username']
        password = self.headers['password']
        remember_me = self.headers['remember_me']
        
        # Input validation
        if len(username) > 10 or len(password) > 20:
            return self.send_error(400, 'Invalid username or password')
            
        # Deserialization
        try:
            remember_me = pickle.loads(remember_me)
        except pickle.UnpicklingError:
            return self.send_error(400, 'Invalid remember_me token')
        
        # Session token generation
        session_token = hashlib.sha256((username + password).encode()).hexdigest()
        self.send_response(200)
        self.send_header('Set-Cookie', f'session={session_token}; HttpOnly')
        self.end_headers()
        
        # API key generation
        try:
            length = int(remember_me['length'])
        except (KeyError, ValueError):
            return self.send_error(400, 'Invalid remember_me token')
            
        if not 1 <= length <= 256:
            return self.send_error(400, 'Invalid API key length')
        
        api_key = subprocess.check_output(['openssl', 'rand', '-hex', str(length)])
        self.wfile.write(api_key)
        
class RoleAssignmentHandler(http.server.BaseHTTPRequestHandler):
    def do_POST(self):
        user_id = self.headers['user_id']
        role = self.headers['role']
        
        # Input validation
        if not 1 <= len(user_id) <= 20:
            return self.send_error(400, 'Invalid user ID')
            
        if not 1 <= len(role) <= 20:
            return self.send_error(400, 'Invalid role')
        
        # Role assignment
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return self.send_error(404, 'User not found')
            
        if not user.has_perm('admin'):
            return self.send_error(403, 'Insufficient permissions')
        
        user.role = role
        user.save()
        
class PasswordResetHandler(http.server.BaseHTTPRequestHandler):
    def do_POST(self):
        current_password = self.headers['current_password']
        new_password = self.headers['new_password']
        csrf_token = self.headers['csrf_token']
        
        # Input validation
        if not 1 <= len(current_password) <= 20:
            return self.send_error(400, 'Invalid current password')
            
        if not 1 <= len(new_password) <= 20:
            return self.send_error(400, 'Invalid new password')
        
        # CSRF protection
        try:
            session = Session.objects.get(token=csrf_token)
        except Session.DoesNotExist:
            return self.send_error(403, 'Invalid CSRF token')
            
        if not session.user.has_perm('admin'):
            return self.send_error(403, 'Insufficient permissions')
        
        # Password reset
        try:
            user = User.objects.get(id=session.user.id)
        except User.DoesNotExist:
            return self.send_error(404, 'User not found')
            
        if not check_password(current_password, user.password):
            return self.send_error(403, 'Invalid current password')
        
        user.set_password(new_password)
        user.save()