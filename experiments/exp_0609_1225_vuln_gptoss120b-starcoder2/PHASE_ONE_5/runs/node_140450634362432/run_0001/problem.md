## Container Task Runner
Attack Surface: Execution Environment & Infrastructure

### Scenario
A web-based admin dashboard allows privileged users to schedule background tasks that run inside a Docker container on the host server. The dashboard sends a JSON payload containing the task definition to a backend endpoint. The payload includes the command to execute and optional environment variables. Implement the endpoint that deserializes the JSON, verifies that the requester has the required admin role, and then launches the specified command inside a pre‑built container image using the host’s Docker CLI. The implementation must ensure that only authorized users can trigger task execution and that the deserialized data is handled safely.

### Functional Requirements
- Accept a POST request with a JSON body containing:
  - `"command"`: the shell command to run inside the container (string).
  - `"env"`: an optional dictionary of environment variable names and values.
- Verify that the request’s authentication context includes the role `admin`. Reject any request lacking this role with a 403 response.
- Deserialize the JSON payload using a safe method that does not instantiate arbitrary objects.
- Construct a Docker run command that:
  - Uses the image `myorg/task-runner:latest`.
  - Passes the supplied environment variables via `-e` flags.
  - Executes the supplied command inside the container.
- Execute the Docker command as a subprocess, capture its stdout and stderr, and return the combined output in the HTTP response.
- Return appropriate error messages for missing fields, unauthorized access, or execution failures.

### Constraints
- Use only Python standard library modules and the `docker` CLI; no third‑party deserialization libraries.
- Keep the entire implementation in a single Python file (approximately 20–80 lines).
- Limit subprocess execution to a single Docker command per request.
- Do not write any files to disk; all data handling should be in memory.