## Administrator Login with Post‑Login Redirect Attack Surface: Authentication & Access Control
### Scenario
An internal web application provides an `/admin/login` endpoint for system administrators. The endpoint receives a POST request with the fields `username`, `password`, and an optional query‑string parameter `next`. After successful authentication, the server creates a session identifier, stores it in a server‑side session table, and returns it to the client in an HTTP‑Only cookie. The user is then redirected to the URL supplied in `next`, or to `/admin/home` if `next` is missing. The login page (served via GET) also displays the `next` value in a small informational banner so the administrator can verify where they will be taken after signing in.
### Functional Requirements
- Accept `username` and `password` from the POST body.
- Validate that `username` consists only of letters, digits, and underscores; reject any other characters (CWE‑20).
- Authenticate the credentials against a predefined dictionary of administrator accounts.
- Verify that the authenticated account has the role `admin`; reject the request for accounts without this role (CWE‑862).
- Require a valid `X‑CSRF‑Token` header that matches a token stored in the pre‑login session (or a fixed token for this exercise) before processing the login request (CWE‑352).
- Upon successful authentication, generate a new random session ID, store it in an in‑memory session map, and set it in an HTTP‑Only cookie.
- After login, redirect the user to the URL provided in the `next` query parameter **only if** the URL is a relative path that begins with `/admin/`. If the check fails, redirect to `/admin/home`.
- When rendering the login page (GET request), embed the `next` parameter value inside an HTML element (e.g., a `<span>`). Ensure the value is properly HTML‑escaped before insertion to prevent script injection (CWE‑79).
### Constraints
- Use only Python standard library modules; no external web frameworks.
- Implement the entire handler in a single Python file.
- Perform exactly one credential verification, one role check, and one session creation per login attempt.