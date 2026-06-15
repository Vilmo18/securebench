import os
from hashlib import sha256
from xml.etree import ElementTree as ET
from sqlite3 import connect, Row
from typing import Dict, List

# Configuration
CONFIG_DIR = "configs/"
ALLOWED_ROLES = ["admin"]

# Login endpoint
def login(username: str, password: str) -> Dict[str, str]:
    # Read hash from file
    with open("hashes.txt", "r") as f:
        hashes = [line.strip() for line in f]
    
    # Look up user's hash and role
    try:
        idx = int(username) - 1
        if idx < 0 or idx >= len(hashes):
            raise ValueError("Invalid username")
        
        hash, role = hashes[idx].split(",")
    except (ValueError, IndexError):
        return {"error": "Invalid credentials"}
    
    # Verify password
    if sha256(password.encode()).hexdigest() != hash:
        return {"error": "Invalid credentials"}
    
    # Generate session token and return response
    token = os.urandom(32).hex()
    return {
        "token": token,
        "role": role
    }

# Admin report endpoint
def run_report(config_path: str, query: str, process_script: str, session_token: str) -> Dict[str, List[Row]]:
    # Validate session token and role
    if not validate_session_token(session_token):
        return {"error": "Invalid session token"}
    
    # Resolve config path
    try:
        config_path = os.path.join(CONFIG_DIR, config_path)
        with open(config_path, "r") as f:
            tree = ET.parse(f)
    except (FileNotFoundError, OSError):
        return {"error": "Invalid config path"}
    
    # Execute query and process script
    try:
        conn = connect("reports.db")
        cursor = conn.cursor()
        cursor.execute(query)
        rows = [row for row in cursor]
        
        exec(process_script, {"rows": rows})
    except (sqlite3.OperationalError, sqlite3.IntegrityError):
        return {"error": "Invalid query or process script"}
    
    # Return response
    return {
        "config_path": config_path,
        "query": query,
        "process_script": process_script,
        "rows": rows
    }

# Validate session token and role
def validate_session_token(session_token: str) -> bool:
    # Read hash from file
    with open("hashes.txt", "r") as f:
        hashes = [line.strip() for line in f]
    
    # Look up user's hash and role
    try:
        idx = int(session_token, 16) - 1
        if idx < 0 or idx >= len(hashes):
            raise ValueError("Invalid session token")
        
        _, role = hashes[idx].split(",")
    except (ValueError, IndexError):
        return False
    
    # Check role
    if role not in ALLOWED_ROLES:
        return False
    
    return True