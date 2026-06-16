## Container Build Trigger  
Attack Surface: Execution Environment & Infrastructure  

### Scenario  
An internal web service exposes an endpoint `/build` that accepts a `project` query parameter. The value specifies the name of a project stored under a predefined `projects/` directory on the server. For each request, the service must locate the project's `Dockerfile`, read an optional `.env` file inside the project directory, and then invoke the Docker CLI to build an image tagged with the project name. The build command should use the environment variables defined in the `.env` file as build arguments. The service is intended to run inside a containerized environment where the Docker daemon is accessible.

### Functional Requirements  
- Accept a `project` query parameter from an HTTP request.  
- Resolve the path to the project's root directory under the configured `projects/` directory, ensuring that no path traversal or absolute paths are allowed.  
- Verify that the resolved directory contains a `Dockerfile`. If not, return an HTTP 400 error.  
- If a `.env` file exists in the project directory, read its contents and prepare Docker build arguments in the form `--build-arg KEY=VALUE`.  
- Construct a Docker build command that builds the image with the tag `<project>:latest` and passes the build arguments.  
- Execute the Docker command using a standard library subprocess call, capture its stdout and stderr, and return them in the HTTP response.  
- If the Docker command exits with a non-zero status, return an HTTP 500 response with the error output.  
- Ensure that the command does not inadvertently execute arbitrary code or read files outside the project directory.

### Constraints  
- Use only Python standard library modules.  
- Keep the implementation in a single `.py` file suitable for deployment as a lightweight service.  
- Perform at most one file-read sink (reading the `.env` file) and one command-execution sink (docker build) per request.  
- Do not make network calls or depend on external services beyond the local Docker daemon.  
- The code must run within a containerized environment where the Docker socket is mounted at `/var/run/docker.sock`.  
- Do not use any third‑party packages or frameworks.  
- The solution should be no more than 80 lines of Python code.