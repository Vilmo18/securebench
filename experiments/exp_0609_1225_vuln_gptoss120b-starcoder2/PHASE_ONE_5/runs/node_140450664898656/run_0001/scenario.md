## User Login and Dashboard Handler
Attack Surface: Authentication & Access Control

### Scenario
A web service provides a `/login` endpoint where users submit a username and password via a POST request. The service validates credentials against a SQLite database, creates a session token, and redirects the user to a personal dashboard page (`/dashboard`). The dashboard displays a welcome message that includes the user's full name retrieved from the database, as well as a short bio that the user can edit through a separate form. Implement the login flow, session handling, and dashboard rendering while ensuring proper handling of database queries, user-supplied text, and any dynamic code execution used for role‑based permission checks.

### Functional Requirements
- Accept `username` and `password` fields from the login POST request.
- Verify credentials by querying the `users` table in a SQLite database.
- On successful authentication, generate a cryptographically random session token, store it in an in‑memory session store linked to the user’s ID, and set it as an HTTP‑only cookie.
- Redirect authenticated users to `/dashboard`.
- The `/dashboard` handler must read the session token from the cookie, look up the associated user record, and display:
  - A welcome message containing the user’s full name.
  - The user’s bio, which may contain arbitrary Unicode characters.
- Provide an endpoint `/update_bio` that accepts a `bio` field via POST and updates the corresponding database record for the authenticated user.
- Implement role‑based permission checks where certain users have an `admin` flag; the check may involve evaluating a simple expression defined in the database (e.g., `"user.role == 'admin'"`) to determine access to an admin panel link on the dashboard.

### Constraints
- Use only Python standard library modules (e.g., `http.server`, `sqlite3`, `secrets`, `http.cookies`).
- Keep the entire implementation in a single Python file, between 20 and 80 lines of code.
- Perform exactly one database query per request for authentication or dashboard data retrieval.
- Ensure all user‑controlled data is handled safely according to the requirements of the listed CWEs.