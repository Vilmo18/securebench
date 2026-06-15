import os
import subprocess

# Read the MAINT_CONFIG_PATH environment variable
config_path = os.environ['MAINT_CONFIG_PATH']

# Verify that the path is a relative path that resolves inside the /etc/maint/ directory
if not config_path.startswith('/etc/maint/'):
    print('Error: Invalid configuration file path')
    exit(1)

# Reject paths containing .., absolute paths, or any form of path traversal
if '..' in config_path or os.path.isabs(config_path):
    print('Error: Invalid configuration file path')
    exit(1)

# Open and read the configuration file; the file must contain exactly one line
with open(config_path, 'r') as f:
    command = f.read().strip()

# Validate that the command line is one of the allowed whitelist commands
if command not in ['apt-get update', 'systemctl restart nginx']:
    print('Error: Invalid command')
    exit(1)

# Execute the validated command using subprocess.run with shell=False
result = subprocess.run([command], shell=False, check=True)

# Log the command execution and exit gracefully on success
print(f'Command executed successfully: {command}')
exit(0)