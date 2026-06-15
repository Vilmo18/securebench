import os
import sys

if len(sys.argv) != 2:
    print("Usage: python logreader.py <log_file>")
    exit(1)

log_file = sys.argv[1]

if not os.environ.get('ROLE') == 'admin':
    print("Unauthorized")
    exit(1)

resolved_path = os.path.realpath(os.path.join('/var/log/app', log_file))

if resolved_path.startswith('/var/log/app') and os.path.isfile(resolved_path):
    with open(resolved_path, 'r') as f:
        print(f.read())
else:
    print("Invalid log path")
    exit(2)