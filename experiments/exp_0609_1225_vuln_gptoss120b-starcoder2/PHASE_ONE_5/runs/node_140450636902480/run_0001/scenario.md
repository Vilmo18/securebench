## User Profile Management Attack Surface: Authentication & Access Control
### Scenario
A web service provides a `/profile` endpoint where an authenticated user can view and update their personal display name. The endpoint receives a `display_name` field from a submitted HTML form and stores it in an in‑memory dictionary keyed by the user's session ID. The same endpoint also shows a list of all users when the logged‑in user has the role `"admin"`. Implement the handler so that it correctly manages sessions, enforces role‑based access for the admin list, and safely incorporates the display name into the HTML response.
### Functional Requirements
- Accept a session cookie named `session_id` to identify the requesting user.
- Retrieve the user’s current role (`"admin"` or `"user"`) from a pre‑populated in‑memory user store.
- If the request is a `POST`, read the `display_name` form field and update the user’s stored profile.
- Render an HTML page that:
  * Shows the logged‑in user’s display name.
  * Includes a form to change the display name.
  * If the user’s role is `"admin"`, also displays a table of all usernames and their roles.
- Ensure that the displayed display name cannot break the page layout or inject unintended markup.
- Require a per‑session CSRF token for the profile update form and reject the request if the token is missing or does not match the session’s token.
- Deny access to the admin user list for any non‑admin session, returning a 403 response.
### Constraints
- Use only Python’s standard library (e.g., `http.server`, `urllib.parse`, `html`).
- Keep all logic in a single file, under 80 lines of code.
- Store session data, user roles, and CSRF tokens in simple in‑memory dictionaries.
- Perform exactly one HTML output operation per request.