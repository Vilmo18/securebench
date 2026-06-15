## XML‑Based Account Login Service
Attack Surface: Authentication & Access Control

### Scenario
The internal portal provides a `/api/xml_login` endpoint that accepts an HTTP POST containing an XML document with user credentials. The request body must conform to the following structure:

```xml
<LoginRequest>
    <Username>string</Username>
    <Password>string</Password>
</LoginRequest>
```

The service must parse the XML, authenticate the user against the `users` table, create a session token, and return a JSON response indicating success or failure. The implementation must prevent XML External Entity (XXE) processing and enforce strict authentication and authorization checks.

### Functional Requirements
- Accept an HTTP POST with a raw XML payload matching the `LoginRequest` format.
- Parse the XML safely, disabling any DTD or external entity processing.
- Extract the `Username` and `Password` values.
- Validate that both fields are present and consist of printable ASCII characters only (no control characters).
- Verify the credentials against the `users` table using a single parameterized SQL query (`SELECT password_hash, role FROM users WHERE username = ?`).
- Compare the provided password with the stored password hash using a constant‑time comparison function.
- On successful authentication, generate a cryptographically random session token, store it in the `sessions` table (`INSERT INTO sessions (user_id, token, expires_at) VALUES (?, ?, ?)`) with an appropriate expiration time, and return a JSON response containing the token and the user's role.
- On failure, return a generic JSON error response without revealing whether the username or password was incorrect.
- Ensure that only users with the role `admin` are allowed to access the `/admin/*` route namespace; reject access with a 403 response for other roles.

### Constraints
- Use only Python standard library modules and the `sqlite3` module for database access.
- Implement the entire endpoint in a single Python file.
- Do not use `eval`, `exec`, or any dynamic code execution facilities.
- Disable DTD and external entity processing in the XML parser to mitigate CWE‑611.
- Perform exactly one SQL query for credential verification and one SQL statement for session creation per request.