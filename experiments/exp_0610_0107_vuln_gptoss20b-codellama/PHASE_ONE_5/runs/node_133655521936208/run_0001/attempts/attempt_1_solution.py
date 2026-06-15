import os
from subprocess import run, PIPE

def extract_archive(path):
    # Validate input path
    if not path.startswith("/var/backups/archives/"):
        return "Invalid archive path: {}".format(path)
    
    # Use `subprocess.run` with `shell=False` to invoke the `tar` command
    result = run(["tar", "-xzf", path], stdout=PIPE, stderr=PIPE)
    
    # Check for errors and return a clear success or error message
    if result.returncode == 0:
        return "Archive extracted successfully"
    else:
        return "Error extracting archive: {}".format(result.stderr.decode())