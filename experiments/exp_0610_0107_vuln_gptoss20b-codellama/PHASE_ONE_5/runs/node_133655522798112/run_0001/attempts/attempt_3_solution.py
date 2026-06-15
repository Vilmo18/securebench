import argparse
import os
import subprocess
import sqlite3
from datetime import datetime

def main():
    parser = argparse.ArgumentParser(description='Start a background service and log the event in a SQLite database.')
    parser.add_argument('service_name', choices=['webserver', 'database', 'cache'], help='The name of the service to start.')
    args = parser.parse_args()

    # Validate input
    if not os.path.exists(os.environ.get('DB_FILE', './service_logs.db')):
        raise ValueError('Database file does not exist.')

    # Build command to start service
    cmd = f'systemctl start {args.service_name}'

    # Execute command and capture exit status
    result = subprocess.run(cmd, shell=False)

    # Insert record into database
    conn = sqlite3.connect(os.environ['DB_FILE'])
    cur = conn.cursor()
    cur.execute('INSERT INTO service_events (service_name, status, timestamp) VALUES (?, ?, ?)', (args.service_name, result.returncode, datetime.now()))
    conn.commit()
    conn.close()

    # Print success message if service started and log entry written
    if result.returncode == 0:
        print(f'Service {args.service_name} started successfully.')
    else:
        print(f'Error starting service {args.service_name}. Exit code: {result.returncode}')
        sys.exit(1)

if __name__ == '__main__':
    main()