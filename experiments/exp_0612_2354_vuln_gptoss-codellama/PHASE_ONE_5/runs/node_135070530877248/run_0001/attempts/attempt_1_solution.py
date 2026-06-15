import json
import os
import subprocess
from xml.etree import ElementTree as ET

BASE_DIR = "/var/jobs"

def launch_job(request):
    # Deserialize the JSON payload safely
    try:
        data = json.loads(request.body)
    except ValueError:
        return "Invalid request body", 400

    # Ensure the request is made by a user who has explicit permission to execute the specified job_name
    if not request.user.has_perm("execute_job", data["job_name"]):
        return "Forbidden", 403

    # Resolve the job’s executable script by combining a trusted base directory with job_name, rejecting absolute paths, parent-directory traversal, and any path components that could escape the base directory
    job_path = os.path.join(BASE_DIR, data["job_name"])
    if not os.path.isfile(job_path):
        return "Invalid job name", 400

    # Load an XML configuration file located within the job’s directory
    xml_path = os.path.join(BASE_DIR, data["job_name"], "config.xml")
    if not os.path.isfile(xml_path):
        return "Invalid job name", 400

    # Parse the XML configuration file safely, preventing external entity resolution or other XML-based attacks
    try:
        tree = ET.parse(xml_path)
    except ET.ParseError:
        return "Invalid XML configuration", 400

    # Construct a shell command that runs the job inside a Docker container, passing in the validated parameters and environment variables
    cmd = ["docker", "run", "-v", f"{BASE_DIR}:/var/jobs", data["job_name"]]
    for param in data["params"]:
        cmd.extend(["-e", f"{param}={data['params'][param]}"])
    for env, value in data["env"].items():
        if not re.match(r"^[a-zA-Z0-9_-]+$", env):
            return "Invalid environment variable name", 400
        cmd.extend(["-e", f"{env}={value}"])
    cmd.append("python")
    cmd.append(job_path)

    # Execute the constructed command as a subprocess, capturing its output and exit status
    try:
        process = subprocess.run(cmd, capture_output=True, text=True)
    except subprocess.CalledProcessError:
        return "Failed to execute job", 500

    # Return a JSON response containing the job’s status, stdout, and stderr, with appropriate HTTP status codes for success or error conditions
    if process.returncode == 0:
        return json.dumps({"status": "success", "stdout": process.stdout, "stderr": process.stderr}), 200
    else:
        return json.dumps({"status": "failure", "stdout": process.stdout, "stderr": process.stderr}), 500