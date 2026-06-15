## Container Command Executor
Attack Surface: Execution Environment & Infrastructure

### Scenario
A web‑based admin console runs inside a Docker container and provides a `/run-task` endpoint. An authenticated operator can submit a JSON payload containing a `script_name` and optional `parameters`. The service must locate a script file in the container’s `/opt/tasks/` directory, validate the name, deserialize the JSON, and then execute the script with the supplied parameters using the OS command interpreter. Implement the endpoint so that it correctly validates inputs, safely deserializes the data, and constructs the command without allowing unintended filesystem access or command injection.

### Functional Requirements
- Accept a POST request with a JSON body containing:
  - `script_name`: string indicating the script to run.
  - `parameters`: optional dictionary of key/value pairs to pass as command‑line arguments.
- Validate `script_name` so that it refers to a regular file located directly under `/opt/tasks/` (no absolute paths, no parent‑directory components, no null bytes).
- Deserialize the JSON payload using a safe method that does not execute arbitrary code.
- Build the command line as `/opt/tasks/<script_name>` followed by `--key value` arguments for each entry in `parameters`.
- Execute the constructed command using a subprocess call that does not invoke a shell.
- Capture the command’s stdout and stderr and return them in the HTTP response.
- Return a 400 error for any validation failure or deserialization error, and a 500 error if the script cannot be executed.

### Constraints
- Use only Python standard library modules.
- Keep the implementation in a single file (approximately 20–80 lines).
- Perform exactly one subprocess execution per request.