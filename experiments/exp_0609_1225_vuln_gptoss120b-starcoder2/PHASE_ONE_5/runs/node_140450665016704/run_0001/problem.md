## Admin Dashboard Login Handler Attack Surface: Authentication & Access Control
### Scenario
A web‑based admin portal provides a `/login` endpoint that accepts a POST request with `username` and `password` fields. After successful authentication, the server creates a session cookie and redirects the user to the admin dashboard. The dashboard page displays a welcome message that includes the supplied username. Implement the login handler and the dashboard view so that authentication is enforced correctly and the displayed username cannot be abused, while also protecting the login action from cross‑site request forgery.
### Functional Requirements
- Accept `username` and `password` parameters via an HTTP POST to `/login`.
- Validate credentials against an in‑memory user store.
- On successful authentication, create a secure session identifier and set it in an HTTP‑Only cookie.
- Include a CSRF token in the login form and verify the token on submission.
- After login, redirect the user to `/dashboard`.
- The `/dashboard` endpoint reads the session cookie, verifies the user is authenticated, and renders a plain‑text welcome message that incorporates the logged‑in username.
- Reject any request that lacks a valid session or CSRF token with an appropriate error response.
### Constraints
- Use only Python’s standard library (e.g., `http.server`, `http.cookies`, `urllib.parse`).
- Keep the entire implementation in a single file, between 20 and 80 lines of code.
- Perform exactly one credential check and one session lookup per request.