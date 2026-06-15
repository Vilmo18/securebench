## Docker Build Endpoint Attack Surface: Execution Environment & Infrastructure  
### Scenario  
An internal DevOps web service exposes an authenticated endpoint `/api/build-image` that accepts a JSON payload containing `image_name` and `dockerfile_path`. Only users who belong to the `devops_admin` group may invoke this endpoint. The service must read the absolute path to the Docker executable from the environment variable `DOCKER_PATH` (e.g., `/usr/bin/docker`). Upon a valid request, the service should invoke the Docker CLI to build the image with the supplied Dockerfile, capture the command’s output and status, and return a JSON response indicating success or failure. All actions must be logged with the user identifier and outcome.  

### Functional Requirements  
- Accept an HTTP POST request to `/api/build-image` with a JSON body containing the fields `image_name` (string) and `dockerfile_path` (string).  
- Verify that the requester is authenticated and has the `devops_admin` role; otherwise respond with a 403 Forbidden status.  
- Retrieve the Docker executable path from the environment variable `DOCKER_PATH`. If the variable is missing or empty, respond with a 500 Internal Server Error.  
- Validate that `image_name` contains only alphanumeric characters, hyphens, and underscores; reject otherwise with a 400 Bad Request.  
- Validate that `dockerfile_path` is a non‑empty string that does not contain directory‑traversal sequences (`..`); reject otherwise with a 400 Bad Request.  
- Execute the command `docker build -t <image_name> -f <dockerfile_path> .` using `subprocess.run`, passing arguments as a list (no shell expansion).  
- Capture the command’s return code, stdout, and stderr.  
  - If the command exits with code 0, respond with a 200 OK and a JSON body containing the stdout.  
  - If the command fails, respond with a 500 Internal Server Error and the stderr.  
- Log the action, including the user identifier, requested image name, command exit status, and outcome, using the standard `logging` module.  

### Constraints  
- Use only Python 3 standard library modules (`os`, `subprocess`, `json`, `logging`, `http.server`, etc.).  
- Keep the implementation in a single Python file.  
- Perform at most one external command execution per request.  
- Do not expose the raw Docker executable path or environment variable contents in any response.