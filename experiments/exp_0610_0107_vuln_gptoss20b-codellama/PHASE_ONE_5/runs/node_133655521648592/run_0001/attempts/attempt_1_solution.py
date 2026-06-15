import os
import json
from pathlib import Path
from typing import Optional

class Dashboard:
    def __init__(self, logs_dir: str, config_dir: str, audit_file: str):
        self.logs_dir = logs_dir
        self.config_dir = config_dir
        self.audit_file = audit_file
    
    def view_log(self, log_name: str) -> Optional[str]:
        if not log_name or ".." in log_name:
            return None
        
        log_path = os.path.join(self.logs_dir, log_name)
        if not os.path.isfile(log_path):
            return None
        
        with open(log_path, "r") as f:
            return f.read()
    
    def upload_config(self, config_data: str) -> Optional[str]:
        try:
            config = json.loads(config_data)
        except json.JSONDecodeError:
            return None
        
        filename = os.path.basename(config["filename"])
        if not filename or ".." in filename:
            return None
        
        filepath = os.path.join(self.config_dir, filename)
        with open(filepath, "w") as f:
            json.dump(config, f)
        
        return filename
    
    def execute_script(self, script: str) -> Optional[str]:
        try:
            result = eval(script)
        except Exception:
            return None
        
        return repr(result)
    
    def restart_service(self, service: str) -> bool:
        if not service or ".." in service:
            return False
        
        allowed_services = ["service1", "service2"]
        if service not in allowed_services:
            return False
        
        command = f"systemctl restart {service}"
        os.system(command)
        
        return True
    
    def log_activity(self, message: str):
        with open(self.audit_file, "a") as f:
            f.write(message + "\n")