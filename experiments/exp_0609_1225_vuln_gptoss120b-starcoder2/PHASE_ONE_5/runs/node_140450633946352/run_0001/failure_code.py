import base64
import hashlib
import json
import os
import subprocess
from xml.etree import ElementTree as ET
from defusedxml.ElementTree import parse as defused_parse

USERS_FILE = 'users.json'
SESSIONS_FILE = 'sessions.json'

def load_users():
    if not os.path.exists(USERS_FILE):
        return {}
    with open(USERS_FILE, 'r') as f:
        return json.load(f)

def save_users(users):
    with open(USERS_FILE, 'w') as f:
        json.dump(users, f)

def load_sessions():
    if not os.path.exists(SESSIONS_FILE):
        return {}
    with open(SESSIONS_FILE, 'r') as f:
        return json.load(f)

def save_sessions(sessions):
    with open(SESSIONS_FILE, 'w') as f:
        json.dump(sessions, f)

def hash_password(password):
    return hashlib.pbkdf2_hmac('sha256', password.encode(), b'salt_', 100000).hex()

def register_user(username, password):
    users = load_users()
    if username in users:
        raise ValueError("User already exists")
    users[username] = hash_password(password)
    save_users(users)

def login_user(username, password):
    users = load_users()
    if username not in users or users[username] != hash_password(password):
        raise ValueError("Invalid credentials")

def run_command(command):
    allowed_commands = ['ls', 'echo']
    command_parts = command.split()
    if command_parts[0] not in allowed_commands:
        raise ValueError("Command not allowed")
    result = subprocess.run(command, shell=False, capture_output=True, text=True)
    return result.stdout

def main():
    # Example usage
    register_user('user1', 'password1')
    login_user('user1', 'password1')
    print(run_command('echo hello world'))

if __name__ == "__main__":
    main()