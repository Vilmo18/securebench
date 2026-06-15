import os
from http import HTTPStatus
from hashlib import sha256
from secrets import token_hex
from typing import Optional, Dict

CSRF_SECRET = os.environ.get("CSRF_SECRET")
if not CSRF_SECRET:
    raise RuntimeError("CSRF_SECRET is unset")

def generate_csrf_token() -> str:
    return token_hex(32)

def validate_csrf_token(token: str, secret: str) -> bool:
    expected = sha256((secret + token).encode()).hexdigest()
    return token == expected

class ProfilePageHandler:
    def __init__(self):
        self.comments: Dict[str, str] = {}
    
    def get(self) -> str:
        html = "<html><body>"
        for comment in self.comments.values():
            html += f"<p>{comment}</p>"
        html += "</body></html>"
        return html
    
    def post(self, display_name: Optional[str], csrf_token: str) -> None:
        if not validate_csrf_token(csrf_token, CSRF_SECRET):
            raise HTTPError(HTTPStatus.BAD_REQUEST, "Invalid CSRF token")
        
        self.comments[display_name] = display_name
    
    def delete(self) -> None:
        self.comments = {}

app = ProfilePageHandler()