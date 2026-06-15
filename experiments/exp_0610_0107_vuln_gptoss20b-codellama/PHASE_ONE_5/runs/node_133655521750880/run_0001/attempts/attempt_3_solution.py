import os
from pathlib import Path
from subprocess import run, PIPE
from typing import Dict, Any

BACKUP_DIR = os.environ["BACKUP_DIR"]

def backup(request: Dict[str, Any]) -> Dict[str, Any]:
    target = request["target"]
    csrf_token = request["csrf_token"]
    
    # Verify authentication and CSRF token
    if not is_authenticated(request) or not validate_csrf_token(csrf_token):
        return {"status": "error", "message": "Invalid credentials"}
    
    # Validate target name
    if not re.match("^[a-zA-Z0-9_-]+$", target):
        return {"status": "error", "message": "Invalid target name"}
    
    # Resolve backup script path
    script_path = Path(BACKUP_DIR, f"{target}/run_backup.sh")
    
    # Confirm subpath of BACKUP_DIR
    if not script_path.parent == BACKUP_DIR:
        return {"status": "error", "message": "Invalid backup script path"}
    
    # Read backup script file
    with open(script_path, "r") as f:
        script = f.read()
    
    # Execute backup script
    result = run(["bash", "-c", script], shell=False, stdout=PIPE, stderr=PIPE)
    
    return {"status": "success", "output": result.stdout}