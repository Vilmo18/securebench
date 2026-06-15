## Container Management Endpoint  
Attack Surface: Execution Environment & Infrastructure

### Scenario
A DevOps dashboard provides an HTTP POST endpoint `/containers/restart` that allows authenticated users to request a restart of a Docker container identified by a `container_name` field in the JSON body. The service reads an environment variable `ALLOWED_CONTAINERS` (a comma‑separated whitelist) to determine which containers may be managed. Implement the handler so it validates the request origin, checks the CSRF token, ensures the requested container is in the whitelist, and safely invokes the Docker CLI to restart the container without exposing command‑injection risks.

### Functional Requirements
- Accept a JSON payload with a `container_name` string.
- Verify that the request includes a valid `X-CSRF-Token` header matching the server‑side token stored in the user's session.
- Parse the `ALLOWED_CONTAINERS` environment variable and confirm that `container_name` is listed.
- Execute the Docker restart command for the specified container using a safe API that does not concatenate untrusted input into a shell command string.
- Return a JSON response indicating success or an appropriate error message (e.g., “invalid token”, “container not permitted”, “restart failed”).

### Constraints
- Use only Python standard library modules and the `subprocess` module for command execution.
- The implementation must reside in a single Python file.
- No external network calls or third‑party services may be required.
- Perform exactly one subprocess call per request.