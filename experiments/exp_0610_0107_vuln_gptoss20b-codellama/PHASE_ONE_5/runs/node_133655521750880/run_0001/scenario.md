## Backup Trigger API Attack Surface: Execution Environment & Infrastructure
### Scenario
A web service offers a `/admin/backup` POST endpoint that allows privileged users to trigger a system‑wide backup. The request body contains a JSON payload with a `target` field specifying the backup destination (e.g., `"daily"`, `"weekly"`). The API must verify that the caller is authenticated as an administrator, confirm a valid CSRF token, resolve the requested backup script located under a directory defined by the `BACKUP_DIR` environment variable, and execute the script to perform the backup.

### Functional Requirements
- Accept a POST request to `/admin/backup` with JSON `{ "target": "<target_name>", "csrf_token": "<token>" }`.  
- Verify that the requester is authenticated and has the `admin` role; otherwise respond with HTTP 403.  
- Validate the CSRF token matches the token stored in the user’s session; otherwise respond with HTTP 403.  
- Ensure `target` matches the regex `^[a-zA-Z0-9_-]+$`; reject any other values.  
- Resolve the backup script path by joining `BACKUP_DIR` (from an environment variable) with the sanitized `target` and the filename `run_backup.sh`.  
- Confirm the resolved path is a subpath of `BACKUP_DIR`; reject if it is not.  
- Read the backup script file (only one file‑read per request).  
- Execute the script using `subprocess.run` with `shell=False`, capturing stdout and stderr.  
- Return a JSON response `{ "status": "success", "output": "<command output>" }` on success, or an error message on failure.

### Constraints
- Use only Python standard library modules.  
- Keep the implementation in a single `.py` file.  
- Perform at most one file‑read operation per request.  
- Do not expose arbitrary command execution or directory traversal.  
- The environment variable `BACKUP_DIR` must be set; if missing, the endpoint should return an informative error.  
- Authentication and CSRF checks must occur for every request.  
- The implementation should be self‑contained and runnable without external services.