## Secure Log File Downloader Attack Surface: Authentication & Access Control
### Scenario
A corporate intranet web app provides an authenticated endpoint `/download_log` that accepts a query parameter `filename`. Only users with role `admin` may request log files. The logs are stored in a server‑side directory `/var/app/logs/`. Implement the endpoint so that it only serves files that reside directly in that directory, rejecting any traversal attempts. The download should be served with appropriate content‑type headers and an attachment disposition. Unauthenticated or non‑admin users should receive a 403 response.

### Functional Requirements
- Accept a `username` and `password` POST to `/login`; establish a session cookie.
- Store user roles; only users with role `admin` can access `/download_log`.
- `/download_log` accepts a `filename` query parameter.
- Resolve the requested file relative to `/var/app/logs/`, without allowing absolute paths or parent directory traversal.
- Serve the file content with `application/octet-stream` MIME type and `Content-Disposition: attachment; filename="..."`.
- Return HTTP 403 for unauthenticated or non‑admin requests.
- Return HTTP 404 for missing or invalid file names.

### Constraints
- Use only Python standard library modules.
- Keep implementation in a single file.
- Perform at most one file‑read operation per request.
- Do not persist session data to disk; keep it in memory for the process.