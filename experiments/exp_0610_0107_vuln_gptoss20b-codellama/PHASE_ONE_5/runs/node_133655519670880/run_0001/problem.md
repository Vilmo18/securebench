## Audit Log Viewer Endpoint Attack Surface: Web Outputs & Rendering
### Scenario
An internal web application provides an endpoint `/admin/logs` that accepts a `logfile` query parameter. Authenticated users with the role `admin` should be able to view the contents of application log files located in `/var/log/myapp/`. The endpoint reads the requested log file and renders its contents inside an HTML page returned to the browser. In addition, the endpoint may invoke a shell command to fetch the last N lines of the file for display. The application must correctly enforce authorization, validate the `logfile` input, prevent path traversal, and avoid command injection in the shell invocation. Error messages displayed to the browser must not reveal sensitive file paths or internal system details.

### Functional Requirements
- Accept an HTTP GET request to `/admin/logs` with a `logfile` query parameter.
- Verify that the requester is authenticated and has the `admin` role; otherwise return HTTP 403.
- Resolve the requested file name to a file under `/var/log/myapp/`; reject absolute paths, relative paths attempting to escape the directory, and paths containing null bytes.
- If the file exists, read its contents and display them in a `<pre>` block within a rendered HTML page.
- Optionally, invoke the system command `tail -n 100 <file>` to display the last 100 lines; this command must be constructed safely to avoid arbitrary command execution.
- For any file not found or error during processing, return an HTTP 404 or 500 status with a generic error message that does not expose server-side file paths or stack traces.
- The HTML response must be UTF-8 encoded and include proper Content-Type headers.

### Constraints
- Use only Python standard library modules (e.g., `http.server`, `os`, `subprocess`).
- Implement the entire handler in a single Python file.
- The handler must perform at most one file-read operation per request.
- Do not write any external files or rely on internet access.