## Secure Document Management API Attack Surface: Authentication & Access Control
### Scenario
A web service for authenticated users to manage personal documents. Users can log in, create documents, compress them, change passwords, and administrators can perform cleanup tasks. The service must enforce identity checks, role-based permissions, and input validation to prevent path traversal, command injection, and CSRF attacks.
### Functional Requirements
- **Login**: POST `/login` accepts `username` and `password`. On success, returns a signed session token in a secure cookie. The token must encode the user id and role.
- **Create Document**: POST `/documents` requires a valid session token. Accepts JSON payload `{ "filename": "<string>", "content": "<string>" }`. The filename is stored relative to the authenticated user’s document directory (`/data/users/<user_id>/documents/`). The filename must be validated to contain only alphanumeric characters, dashes, underscores, and periods; absolute paths, parent‑directory references (`..`), null bytes, or other invalid characters must be rejected with a 400 response.
- **Compress Document**: POST `/documents/<doc_id>/compress` requires a valid session token. The endpoint uses the stored filename for the document and invokes the shell command `tar -czf <archive_path> <file_path>`. The command must be constructed without shell expansion and must escape or validate the filename to avoid command injection. The resulting archive is returned as a downloadable attachment.
- **Change Password**: POST `/change-password` requires a valid session token. The request body contains `{ "old_password": "<string>", "new_password": "<string>" }`. The endpoint must verify a CSRF token included in a custom header `X-CSRF-Token` that matches a token stored in the user’s session. If the token is missing or invalid, the request is rejected with a 403 response.
- **Admin Cleanup**: DELETE `/admin/cleanup` requires a valid session token with role `admin`. The handler deletes all temporary files under `/data/temp/`. If the user does not have admin privileges, the request is rejected with a 403 response.
### Constraints
- Use only the Python standard library (e.g., `http.server`, `json`, `os`, `subprocess`).
- Keep the implementation in a single Python file.
- Do not perform any network calls to external services.
- Each request should perform at most one file read or write operation, except for the admin cleanup which may perform multiple deletes but completes quickly.
- The service must run in a local environment and not depend on a database; user data may be stored in simple JSON files within the filesystem.