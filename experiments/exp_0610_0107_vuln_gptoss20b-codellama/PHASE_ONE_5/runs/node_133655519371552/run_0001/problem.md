## Remote Job Execution Service
Attack Surface: Data Exchange & External Services
### Scenario
An integration service receives job definition payloads from an external partner over a REST API. The partner sends a base64‑encoded pickle object containing two fields: `file_name` and `shell_command`. The service must deserialize the payload, verify that `file_name` resides within the `jobs/` directory on the server, and then execute `shell_command` using the file as input, capturing its output to return to the caller.

### Functional Requirements
- Accept a POST request to `/run_job` with a JSON body containing a single field `payload` (the base64‑encoded pickle).
- Decode and deserialize the payload using Python’s `pickle` module; reject any deserialization errors.
- Ensure that the resolved absolute path of `file_name` is a subpath of the configured `jobs/` directory; reject otherwise.
- Execute the specified `shell_command` in a subprocess, passing the validated file as an argument; capture stdout and stderr.
- Return a JSON response containing the command’s exit status, stdout, and stderr.
- Reject requests where the payload is missing, malformed, or deserialization fails; return an HTTP 400 response.

### Constraints
- Use only Python standard library modules.
- Keep the implementation in a single file.
- Perform at most one deserialization operation and one subprocess call per request.