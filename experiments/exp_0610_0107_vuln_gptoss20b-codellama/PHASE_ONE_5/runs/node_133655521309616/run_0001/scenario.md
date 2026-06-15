## Secure Session and Role Management System Attack Surface: Authentication & Access Control
### Scenario
A small web service provides authenticated users with a session ticket and role-based access to administrative functions. The system must support:
- User login via a `/login` endpoint that accepts a username, password, and an optional serialized “remember_me” payload.  
- Creation of a session token that is stored in an HTTP‑only secure cookie.  
- Generation of a unique API key by invoking an external shell tool, using the user‑provided key length parameter.  
- An `/admin/assign_role` endpoint that accepts a JSON payload containing a target user ID and role. The payload is deserialized and used to update the user’s role in the database.  
- A `/reset_password` endpoint that allows an authenticated user to change their password; the request must include a CSRF token to prevent cross‑site request forgery.  
All operations must enforce proper identity checks and permission validation before performing any state changes.

### Functional Requirements
- **Login** – Accept `username`, `password`, and optional `remember_me` (a base64‑encoded pickled token).  
- **Input Validation** – Reject usernames or passwords containing null bytes or exceeding reasonable length limits.  
- **Deserialization** – Safely deserialize the `remember_me` payload, ensuring it contains only expected fields.  
- **Session Token** – Generate a signed JWT containing the user ID and role, set it in an HTTP‑only secure cookie.  
- **API Key Generation** – Execute a shell command (e.g., `openssl rand -hex <length>`) where `<length>` is derived from user input; validate that `<length>` is a positive integer within a safe range to avoid command injection.  
- **Role Assignment** – Deserialize the JSON payload; verify the requester has admin privileges before updating the target user’s role in the database.  
- **Password Reset** – Require a valid CSRF token; update the stored password hash only after verifying the current password.  

### Constraints
- Use only Python standard library modules (e.g., `http.server`, `pickle`, `hashlib`, `subprocess`).  
- Keep the entire implementation in a single `.py` file.  
- Perform no more than one external shell command per request and one database write per endpoint.  
- Ensure all user‑supplied data is validated or sanitized before use in any system operation.  
- The CSRF protection mechanism must be implemented using a randomly generated token stored in the session.