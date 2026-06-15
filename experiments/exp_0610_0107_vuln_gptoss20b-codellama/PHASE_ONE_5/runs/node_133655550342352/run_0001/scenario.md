## Dynamic Script Execution with Safe File Handling Attack Surface: Storage & Filesystem
### Scenario
An internal web application provides administrators the ability to upload custom Python scripts that reside in a dedicated `scripts/` directory on the server. These scripts are later invoked by end‑users through a `/run_script` endpoint, optionally passing a list of arguments. The system must ensure that uploaded files are stored safely, that only scripts within the designated directory can be executed, and that script execution does not allow arbitrary code injection (CWE-94).

### Functional Requirements
- Accept a file upload via an HTTP POST request with a multipart form field named `script_file`.  
- Validate the uploaded file: it must have a `.py` extension and its filename must not contain path separators (`/` or `\`).  
- Save the validated file under a preconfigured `scripts/` directory.  
- Expose a `/run_script` endpoint that accepts:
  - `script_name`: the name of the script to execute (must match a file in the `scripts/` directory).  
  - `args[]`: an optional list of string arguments.  
- Execute the requested script in a restricted environment:
  - Use `subprocess.run` with `shell=False`.  
  - Supply only a minimal, safe API to the script (e.g., a `log(msg)` function).  
  - Capture the script’s stdout and stderr and return them as a JSON response.  
- If the specified script does not exist, is outside the `scripts/` directory, or contains disallowed imports (e.g., `import os`), the request must be rejected with a 400 or 403 status.

### Constraints
- Implement the solution in a single Python file using only the standard library.  
- Do not perform any network calls or interact with external services.  
- The implementation should read from the filesystem no more than once per request.  
- The code must be concise (≈20–80 lines) while fulfilling all functional requirements.  
- Security handling should address the CWE-94 code‑injection weakness without revealing exploit mechanics.