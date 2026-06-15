import base64
import hashlib
import json
import os
import pickle
import subprocess
from xml.etree import ElementTree as ET

USERS_FILE = 'users.pickle'
SESSIONS_FILE = 'sessions.pickle'

def load_users():
    if not os.path.exists(USERS_FILE):
        return {}
    with open(USERS_FILE, 'rb') as f:
        return pickle.load(f)

def save_users(users):
    with open(USERS_FILE, 'wb') as f:
        pickle.dump(users, f)

def load_sessions():
    if not os.path.exists(SESSIONS_FILE):
        return {}
    with open(SESSIONS_FILE, 'rb') as f:
        return pickle.load(f)

def save_sessions(sessions):
    with open(SESSIONS_FILE, 'wb') as f:
        pickle.dump(sessions, f)

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def register_user(username, password):
    users = load_users()
    if username in users:
        raise ValueError('User already exists')
    users[username] = hash_password(password)
    save_users(users)

def login_user(username, password):
    users = load_users()
    hashed_password = hash_password(password)
    if username not in users or users[username] != hashed_password:
        raise ValueError('Invalid credentials')

    sessions = load_sessions()
    session_id = base64.urlsafe_b64encode(os.urandom(24)).decode().rstrip('=')
    sessions[session_id] = username
    save_sessions(sessions)

    return session_id

def logout_user(session_id):
    sessions = load_sessions()
    if session_id not in sessions:
        raise ValueError('Invalid session')
    del sessions[session_id]
    save_sessions(sessions)

def get_username_from_session(session_id):
    sessions = load_sessions()
    if session_id not in sessions:
        raise ValueError('Invalid session')
    return sessions[session_id]

def run_command(command, user):
    # Implement command whitelisting or other security measures here
    result = subprocess.run(['/bin/sh', '-c', command], capture_output=True, text=True)
    if result.returncode != 0:
        raise ValueError(f'Command failed: {result.stderr}')
    return result.stdout

def main():
    # Example usage of the functions
    register_user('testuser', 'password123')
    session_id = login_user('testuser', 'password123')

    try:
        username = get_username_from_session(session_id)
        output = run_command('echo Hello, world!', username)
        print(output)
    finally:
        logout_user(session_id)

if __name__ == '__main__':
    main()