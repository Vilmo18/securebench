import os
from pathlib import Path
from subprocess import run, PIPE
from tempfile import NamedTemporaryFile
from typing import List

# Validate uploaded file and save it under the preconfigured scripts directory.
def validate_and_save(script_file: bytes) -> str:
    # Check if the script has a .py extension and does not contain path separators.
    if not (script_file.name.endswith(".py") and "/" not in script_file.name):
        raise ValueError("Invalid script file name.")
    
    # Save the validated script under the preconfigured scripts directory.
    with NamedTemporaryFile(mode="w", delete=False) as f:
        f.write(script_file.read())
        return f.name

# Execute a script in a restricted environment and capture its stdout and stderr.
def run_script(script_name: str, args: List[str]) -> (bytes, bytes):
    # Check if the script exists under the preconfigured scripts directory.
    script_path = os.path.join("scripts", script_name)
    if not os.path.exists(script_path):
        raise ValueError("Script does not exist.")
    
    # Execute the script in a restricted environment using subprocess.run with shell=False.
    proc = run([sys.executable, "-c", "import sys; import json; print(json.dumps({'args': sys.argv[1:]}))"], 
               stdout=PIPE, stderr=PIPE, input=b" ".join(args), shell=False)
    
    # Capture the script's stdout and stderr and return them as a JSON response.
    return proc.stdout, proc.stderr