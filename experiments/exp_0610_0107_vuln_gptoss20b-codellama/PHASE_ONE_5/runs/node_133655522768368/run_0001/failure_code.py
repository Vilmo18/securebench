import os
import pickle
import subprocess
from base64 import b64decode

def run_command(cmd):
    try:
        proc = subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return proc.stdout.decode('utf-8')
    except subprocess.CalledProcessError as e:
        print(f'Command failed with exit code {e.returncode} and error message: {e.stderr.decode("utf-8")}')
        sys.exit(1)

def main():
    try:
        config = pickle.loads(b64decode(os.environ['WORKER_CONFIG']))
    except (KeyError, ValueError):
        print('Missing or invalid WORKER_CONFIG environment variable')
        sys.exit(1)
    
    try:
        action = config['action']
    except KeyError:
        print('Invalid configuration dictionary')
        sys.exit(1)
    
    if not isinstance(action, str):
        print('Action must be a string')
        sys.exit(1)
    
    if action not in ['ping', 'hostname', 'uptime']:
        print(f'Invalid command: {action}')
        sys.exit(1)
    
    output = run_command([action])
    print(output)

if __name__ == '__main__':
    main()