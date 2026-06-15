## Service Configuration Import/External Webhook Receiver  
Attack Surface: Data Exchange & External Services  
### Scenario  
An internal configuration management system exposes a `/api/config/webhook` endpoint to receive automated configuration updates from third‑party services. The endpoint accepts either JSON or XML payloads. Each payload includes:  
- `name`: the configuration identifier.  
- `description`: a free‑text field that is later rendered in the web‑based admin dashboard.  
- `script`: a snippet of Python code that the system will execute to apply configuration changes.  
- `csrf_token`: a token that must match the authenticated session’s token.  

The system must validate the request, safely process the payload, execute the script in a restricted environment, and store the configuration.  

### Functional Requirements  
- Accept HTTP POST requests to `/api/config/webhook` with `Content-Type` of `application/json` or `application/xml`.  
- Parse the payload, extracting the four fields listed above.  
- Verify that the `csrf_token` matches the token associated with the current user session; otherwise respond with HTTP 403.  
- For JSON payloads, reject any fields that contain unexpected keys or are of incorrect type; for XML payloads, reject any malformed documents or uses of external entities.  
- Escape or otherwise sanitize the `description` value before it is displayed in the admin UI to prevent untrusted content from executing in user browsers.  
- Execute the `script` value in a sandboxed, read‑only environment that allows only a predefined set of safe operations (e.g., modifying configuration entries, reading system state). Deny execution if the script references disallowed modules, functions, or performs prohibited operations.  
- Persist the validated `name`, sanitized `description`, and any configuration state derived from the script into the system’s database.  
- Respond with HTTP 200 and a JSON body confirming success, or an appropriate error status code and message if any validation fails.  

### Constraints  
- Use only Python standard library modules.  
- Implement the entire handler in a single `.py` file.  
- The handler must perform at most one database write operation per request.  
- All input validation, parsing, sanitization, and execution steps must be deterministic and not rely on external services or network access.