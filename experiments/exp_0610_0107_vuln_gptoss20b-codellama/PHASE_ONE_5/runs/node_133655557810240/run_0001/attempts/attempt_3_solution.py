import os
import subprocess

def backup_database(backup_dir):
    # Validate the backup directory path
    if not backup_dir.startswith('/'):
        raise ValueError('Backup directory must be an absolute path')
    if '..' in backup_dir:
        raise ValueError('Backup directory cannot contain parent-directory traversal sequences')
    
    # Compose the Docker exec command
    cmd = ['docker', 'exec', '-it', 'mysql-container', 'mysqldump', '--result-file', f'{backup_dir}/db.sql']
    
    # Execute the command and capture output and error streams
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    
    # Log the backup result
    if result.returncode == 0:
        print('Backup successful')
    else:
        print('Backup failed with error code', result.returncode)
        print(result.stderr.decode())
    
    return result.returncode