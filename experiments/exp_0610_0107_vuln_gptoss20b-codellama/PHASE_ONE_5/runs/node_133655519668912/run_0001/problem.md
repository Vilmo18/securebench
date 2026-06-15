## Secure Webhook Processor Attack Surface: Data Exchange & External Services
### Scenario
An automated monitoring platform exposes a webhook endpoint `/api/v1/process` that accepts POST requests from an external analytics service. Each request contains a JSON payload specifying the relative path of a data file to be processed and an optional action command (e.g., `"compress"`). The platform must authenticate the caller, safely deserialize the JSON, validate the file path to prevent directory traversal, execute the requested action as an operating‑system command without shell expansion, and return a JSON result indicating success or failure.

### Functional Requirements
- Accept a POST request to `/api/v1/process` with a JSON body.  
- Require a valid `X-API-Key` header for authorization; reject requests lacking a key or with an invalid key with a 401 response.  
- Safely deserialize the request body using the standard library JSON parser; reject malformed or non‑JSON payloads with a 400 response.  
- Extract the `file_path` field; ensure it is a relative path that resolves inside a preconfigured data directory (e.g., `/var/data/`). Reject absolute paths, paths containing `..`, or any that resolve outside the allowed directory with a 400 response.  
- Extract the optional `action` field; allow only a predefined whitelist of safe commands (e.g., `compress`, `analyze`). For any other value, reject the request with a 400 response.  
- Execute the chosen action by invoking the corresponding system command via `subprocess.run` with `shell=False`, passing the validated file path as an argument. Capture stdout and stderr.  
- Return a JSON response containing `status` (`"ok"` or `"error"`), `output` (command stdout), and `error` (stderr or error message).  
- Log each request and its outcome for audit purposes.

### Constraints
- Use only Python standard library modules.  
- Keep the entire implementation in a single source file.  
- Read at most one file from disk per request.  
- Do not expose any service or serialization boundary to untrusted data without validation.