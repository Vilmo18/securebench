import os
from pathlib import Path
from subprocess import run, PIPE
from http import HTTPStatus

def compress(path):
    # Resolve the requested path relative to /srv/data/
    resolved_path = Path("/srv/data") / path.strip("/")
    
    # Reject absolute paths and parent-directory traversal (..)
    if resolved_path.is_absolute() or ".." in str(resolved_path):
        return HTTPStatus.BAD_REQUEST, None
    
    # Verify that the resolved path points to an existing regular directory
    if not resolved_path.exists() or not resolved_path.is_dir():
        return HTTPStatus.NOT_FOUND, None
    
    # Use subprocess.run with a list of arguments (no shell=True) to execute tar -czf - <resolved_directory> and capture its stdout as the compressed archive
    result = run(["tar", "-czf", "-", str(resolved_path)], stdout=PIPE, check=True)
    
    # Return a 200 response with the archive data, setting Content-Type: application/gzip and Content-Disposition: attachment; filename="<directory>.tar.gz"
    return HTTPStatus.OK, result.stdout, {"Content-Type": "application/gzip", "Content-Disposition": f'attachment; filename="{resolved_path.name}.tar.gz"'}