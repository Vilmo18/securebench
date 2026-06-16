## Configuration Upload Handler Attack Surface: Storage & Filesystem
### Scenario
An enterprise web application allows administrators to upload a configuration file that the server deserializes to update application settings.  
- The uploaded file is a Python pickle object containing a `log_directory` field specifying where the application should write its logs.  
- The server accepts the file through a `/admin/upload_config` endpoint.  
- After deserialization, the server writes a status log to the directory defined in the payload.  
- The endpoint is reachable by any authenticated user; only users with the role `ADMIN` should be permitted to upload and apply configurations.  
- The server must prevent path‑traversal attacks that could redirect logs outside the intended logs directory and must validate that the deserialization process does not execute arbitrary code.
### Functional Requirements
- Accept a multipart/form‑data request with a file field named `config_file`.  
- Verify the request comes from a user whose role is `ADMIN`; reject all others with a 403 response.  
- Deserialize the uploaded file using a safe method that does not execute arbitrary code (e.g., `pickle.loads` with a restricted `RestrictedUnpickler` or equivalent).  
- Extract the `log_directory` value from the deserialized object and ensure it resolves to a subdirectory of the server’s configured `logs/` directory. Reject any absolute paths, paths containing `..`, or paths that resolve outside `logs/`.  
- Create the target log directory if it does not exist, with secure permissions.  
- Write a simple status entry to a file named `config_update.log` inside the validated log directory.  
- Return a 200 OK response on success; for any invalid input, authorization failure, or disallowed path, return an appropriate error status (400, 403, or 404).  
### Constraints
- Use only Python standard library modules.  
- Implement the entire handler in a single Python file.  
- Perform at most one deserialization sink and one file‑write sink per request.  
- Do not use any external configuration or environment variables beyond a hard‑coded `LOGS_ROOT = "logs/"`.  
- Ensure the system does not expose any other filesystem or network resources.