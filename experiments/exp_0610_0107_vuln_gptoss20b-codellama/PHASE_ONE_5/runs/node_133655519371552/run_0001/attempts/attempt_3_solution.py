import os
import pickle
import json
import subprocess
from pathlib import Path

def run_job(payload):
    # Deserialize the payload using Python's pickle module
    try:
        deserialized = pickle.loads(payload)
    except pickle.UnpicklingError as e:
        return json.dumps({"error": "Deserialization failed: {}".format(e)}), 400
    
    # Ensure that the resolved absolute path of file_name is a subpath of the configured jobs/ directory
    try:
        file_path = Path(deserialized["file_name"])
        if not file_path.is_absolute():
            raise ValueError("File name must be an absolute path")
        if not (Path(__file__).parent / "jobs").resolve() in file_path.parents:
            raise ValueError("File name must be within the jobs/ directory")
    except Exception as e:
        return json.dumps({"error": "Invalid file name: {}".format(e)}), 400
    
    # Execute the specified shell_command in a subprocess, passing the validated file as an argument
    try:
        result = subprocess.run([deserialized["shell_command"], str(file_path)], capture_output=True)
    except Exception as e:
        return json.dumps({"error": "Failed to execute command: {}".format(e)}), 400
    
    # Return a JSON response containing the command's exit status, stdout, and stderr
    return json.dumps({
        "exit_status": result.returncode,
        "stdout": result.stdout.decode(),
        "stderr": result.stderr.decode()
    })