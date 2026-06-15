## Admin Portal with Authenticated File Access
Attack Surface: Authentication & Access Control
### Scenario
A corporate web service offers a protected portal where users must log in to obtain a session cookie. Inside the portal, administrators can delete user accounts, while all authenticated users can request files from a specific directory on the server. The system must enforce session validation, role‑based authorization, CSRF protection for state‑changing actions, and strict path validation to prevent directory traversal.

### Functional Requirements
- **Login** – POST `/login` receives `username` and `password`. On success, create a session cookie marked HttpOnly, Secure, and associate the user’s role (`admin` or `user`). The user’s ID is stored in the session.
- **CSRF Token** – GET `/csrf-token` returns a cryptographically random token tied to the current session. The token must be supplied in the `X-CSRF-Token` header for any request that modifies state.
- **Delete User** – DELETE `/admin/delete_user` accepts JSON `{ "user_id": <int> }`. The request is allowed only if the session is active, the user role is `admin`, and a valid CSRF token is provided. The specified user record is removed from an in‑memory dictionary.
- **File Download** – GET `/download?path=<relative_path>` serves files from a fixed `protected_files/` directory. The `path` query must be validated to reject absolute paths, parent‑directory traversals, null bytes, and any characters that could escape the directory. The file is streamed as a binary response with the appropriate MIME type.
- **Audit Logging** – Log each request with timestamp, session user ID, endpoint accessed, and outcome (success or failure).

### Constraints
- Implement the service entirely in a single Python file using only the standard library.
- Use in‑memory data structures for user accounts, sessions, and CSRF tokens.
- Perform no more than one file read operation per incoming request.
- Ensure session cookies are regenerated on each successful login and invalidated on logout or session expiration.