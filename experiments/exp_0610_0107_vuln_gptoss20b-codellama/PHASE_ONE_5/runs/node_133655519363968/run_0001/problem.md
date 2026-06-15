## Dynamic Administration Console
Attack Surface: Execution Environment & Infrastructure
### Scenario
An internal web console accepts a JSON POST request from an administrator to run a server‑side command, process a serialized data payload, optionally execute Python code, and return an HTML report that displays the command output and user‑supplied content. The console reads configuration values from environment variables and enforces CSRF protection, command whitelisting, safe deserialization, optional dynamic code execution, and safe HTML rendering.

### Functional Requirements
- Accept a JSON body with keys: `cmd` (string), `payload` (JSON string), `script` (optional Python code), `html` (string), and `csrf_token` (string).  
- Validate `csrf_token` against the value stored in the `ADMIN_CSRF_TOKEN` environment variable. Reject the request if the token is missing or mismatched.  
- Validate that `cmd` is one of a predefined whitelist of safe system commands (e.g., `['uptime', 'date', 'whoami']`). Reject any other values.  
- Deserialize `payload` safely using the standard library’s `json` module. Reject the request if the payload contains non‑primitive JSON types beyond a simple dictionary of strings to numbers.  
- If the `ENABLE_DYN_CODE` environment variable is set to `true`, evaluate the `script` field using `exec` in a restricted namespace that contains only the `payload` dictionary. If the variable is not set or is `false`, ignore the `script` field.  
- Execute the validated `cmd` using a subprocess call that captures its standard output.  
- Render an HTML page that includes the captured command output and the `html` field provided by the client. The final page is sent as the HTTP response.

### Constraints
- All operations must be performed within a single Python file using only the standard library.  
- No external services or network calls are required.  
- The implementation must use environment variables for configuration and CSRF token storage.  
- The design should not rely on any third‑party web frameworks; a simple WSGI or socket server is acceptable.  
- The final HTML response should be the only data‑flow sink for user‑supplied content.