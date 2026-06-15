import base64
from json import loads
from pickle import Unpickler, PicklingError
from typing import Any

class Command:
    def __init__(self, command: str):
        self.command = command

def process(request: Any) -> Any:
    try:
        payload = request.json()["payload"]
        decoded_bytes = base64.b64decode(payload)
        unpickler = Unpickler(decoded_bytes)
        obj = unpickler.load()
        if not isinstance(obj, Command):
            raise PicklingError("Invalid payload")
        command = obj.command
    except (KeyError, ValueError, PicklingError):
        return {"status": "error", "message": "Invalid request"}
    
    # Log the request method, endpoint, and extracted command value for audit purposes
    print(f"{request.method} {request.path}: {command}")
    
    return {"status": "ok", "command": command}