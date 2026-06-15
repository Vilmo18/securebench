## Log File Retrieval Service Attack Surface: Execution Environment & Infrastructure
### Scenario
A system administration web console provides a `/admin/get_log` endpoint that allows authorized operators to view log files from the server. The request is an HTTPS GET with a query parameter `log_path` that specifies the relative path of the log file to retrieve (e.g., `app/error.log`). The service must verify that the caller is authenticated via a session cookie, restrict the operation to the predefined log directory (`/var/log/myapp/`), and read the requested file content to return it in the HTTP response. Implement the handler so that it safely resolves the requested path, prevents directory traversal outside the allowed log directory, and handles missing or disallowed files gracefully.

### Functional Requirements
- Accept only GET requests with a `log_path` query parameter.
- Verify that the request is associated with an authenticated admin session.
- Resolve `log_path` against the base directory `/var/log/myapp/` and ensure the final resolved path remains within this directory.
- Reject any request that attempts to escape the base directory (e.g., using `..` or absolute paths) and return a 403 response.
- If the resolved file does not exist or is not a regular file, return a 404 response.
- Read the allowed log file and return its contents with a `text/plain` content type.
- Limit the response size to a maximum of 1 MiB; truncate larger files and indicate truncation in the response body.

### Constraints
- Use only Python standard library modules.
- All code must be contained in a single Python file.
- Perform at most one file‑read operation per request.
- No external network calls are required beyond handling the incoming HTTP request.