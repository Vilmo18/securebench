## Dynamic Task Executor
Attack Surface: User Inputs & Data
### Scenario
An internal web service provides a `/run_task` endpoint that accepts a multipart POST request. The payload includes:
- A file upload named `config` containing a pickled Python object that specifies task parameters.
- A query parameter `script` that contains a snippet of Python code to be executed as part of the task.

Only users with an active session cookie are allowed to invoke the endpoint. The service deserializes the uploaded configuration, evaluates the supplied script, builds a shell command based on these inputs, and executes the command. The output of the command and any script return value are sent back as the HTTP response body.

### Functional Requirements
- Validate that the request includes a valid session cookie identifying an authorized user; otherwise, return a 401 Unauthorized response.
- Accept the multipart form data containing a file named `config`. Ensure the file is a valid pickle and contains only safe types (e.g., primitive data, lists, dicts) before deserialization.
- Retrieve the `script` query parameter, confirm it is a non-empty string, and evaluate it in a sandboxed environment that limits available built‑ins and modules.
- Construct a shell command that incorporates the deserialized configuration values and the result of the script evaluation. The command must be built in a manner that prevents shell injection.
- Execute the constructed command using a subprocess call that does not invoke a shell interpreter unless absolutely necessary, capturing its stdout and stderr.
- Return the captured output as the HTTP response body with a 200 OK status. If any validation fails, return an appropriate HTTP error status.

### Constraints
- Use only Python 3.11 standard library modules (e.g., `pickle`, `subprocess`, `http.server`, `cgi`, `os`).
- Keep the implementation in a single Python file.
- The service should read at most one file from the request per invocation.
- All inputs must be treated as untrusted and validated according to the requirements above.