## Secure User Profile Viewer Attack Surface: Web Outputs & Rendering
### Scenario
A web application provides a `/profile/<user_id>` page that displays a user’s name, email address, and recent activity. The user is identified by a session cookie that contains `user_id` and `role`. Only the profile owner or a user with the `"admin"` role may view the page. Attempts by other users must receive a 403 Forbidden response with a generic error message. No profile information should appear in redirects, error pages, or reflected input.

### Functional Requirements
- Accept an HTTP GET request to `/profile/<user_id>` and extract the targeted `user_id` from the URL path.
- Read the requester’s `user_id` and `role` from a session cookie stored in a server‑side session map.
- Retrieve the requested profile from an in‑memory user database keyed by `user_id`.
- If the requester’s `user_id` matches the requested `user_id` **or** the requester’s `role` is `"admin"`, render an HTML page showing the profile’s name, email, and recent activity.
- If the authorization check fails, respond with HTTP 403 Forbidden and a generic error message; do not expose any profile data.
- If the requested `user_id` does not exist in the database, respond with HTTP 404 Not Found and a generic error message.

### Constraints
- Use only Python standard library modules (e.g., `http.server`, `http.cookies`, and plain string formatting for HTML).
- The entire implementation must be contained in one file and perform at most one database lookup per request.
- Session handling can be simulated with a hard‑coded in‑memory session store mapped by cookie value.