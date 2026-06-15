## System Configuration Update Endpoint Attack Surface: Execution Environment & Infrastructure
### Scenario
A lightweight HTTP service exposes a `/config/update` POST endpoint that accepts a JSON payload from a user. The payload contains three fields:
1. `file_path` – the relative path of a configuration file to be updated.
2. `commands` – a list of shell commands that should be executed to modify the file.
3. `env` – a dictionary of environment variables to be set during command execution.

The service runs within a containerized environment where all configuration files are located under `/app/config`. The intended behavior is to safely resolve the requested file, apply the supplied commands with the provided environment settings, and return the outcome of the operation. The endpoint should enforce that only files under `/app/config` are targeted, that the requester is authorized to perform updates, that the request includes a valid CSRF token, and that the supplied commands are executed in a controlled manner without allowing arbitrary code injection.

### Functional Requirements
- Accept a POST request to `/config/update` with Content-Type `application/json`.
- Parse the JSON payload, extracting `file_path`, `commands`, and `env`.
- Resolve `file_path` relative to `/app/config`; reject any path that resolves outside this directory.
- Verify that the requester’s session is authenticated and holds the `admin` role; reject otherwise.
- Validate the presence of a CSRF token in the request header `X-CSRF-Token`; reject if missing or invalid.
- For each command in `commands`, execute it using the `subprocess` module with the specified `env` variables, ensuring that the current working directory is `/app/config`.
- Capture stdout, stderr, and exit status for each command and include them in the JSON response.
- Return a JSON response with `status: success` or `status: error` and relevant details.
- Log each update attempt, including the authenticated user, target file, and outcome.

### Constraints
- Implement the service in a single Python file using only the standard library (e.g., `http.server`, `json`, `subprocess`, `os`, `urllib.parse`).
- Do not write or read any files outside `/app/config`.
- Do not allow arbitrary file paths or command injection through the payload.
- Keep the implementation within 80 lines of code. 
- Ensure that each request results in at most one file-write operation per command execution. 
- All user input must be validated before being used in file resolution or command execution.