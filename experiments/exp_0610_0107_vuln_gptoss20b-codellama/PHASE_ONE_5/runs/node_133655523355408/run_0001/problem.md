## Secure Dynamic Script Execution Service Attack Surface: User Inputs & Data
### Scenario
A web API endpoint `/execute` accepts a POST request with a JSON payload. The payload contains three fields:
* `target_file`: a relative file path indicating where the script’s output should be written.
* `script`: a plain‑text string of Python code that will be executed.
* `payload`: a base64‑encoded string that, when decoded, must be deserialized (using the `pickle` module) to produce a Python object which the script may use.

The API is the sole boundary between untrusted user input and the service’s internal logic. The service must validate and sanitize every part of the input before any file system access, deserialization, or code execution occurs.

### Functional Requirements
- Accept and parse a JSON body containing `target_file`, `script`, and `payload` fields.  
- Validate `target_file` to ensure it is a non‑empty relative path that resolves inside a predefined safe directory; reject absolute paths, null bytes, parent‑directory traversal sequences, and any path that would escape the safe directory.  
- Decode `payload` from base64, then deserialize it with `pickle`. The deserialization step must be performed in a way that prevents execution of arbitrary code during unpickling.  
- Validate the `script` string to guarantee that it does not contain disallowed imports (e.g., `os`, `subprocess`), disallowed built‑ins, or patterns that could lead to code injection.  
- Execute the validated `script` in a restricted namespace, providing it access only to the deserialized payload object and a limited set of safe helper functions.  
- Capture the script’s stdout or a predefined result value, then write that result atomically to the `target_file` inside the safe directory.  
- Return a JSON response indicating success or failure, with appropriate HTTP status codes.  

### Constraints
- Use only Python’s standard library; no external dependencies are allowed.  
- Implement the entire service logic in a single Python file (≤ 80 lines).  
- Perform at most one file-write operation per request.  
- Enforce a strict time‑out on script execution to prevent denial‑of‑service.  
- Log all validation errors and execution failures for audit purposes.  

This ticket specifies all requirements for a secure implementation that must handle untrusted user inputs, prevent path traversal, guard against unsafe deserialization, and control execution of user‑supplied code.