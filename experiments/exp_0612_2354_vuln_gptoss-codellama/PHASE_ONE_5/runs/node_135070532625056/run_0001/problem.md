## Secure Profile Service Implementation Ticket Attack Surface: Authentication & Access Control
### Scenario
A small web application offers user‑centric profile functionality. Registered users log in with a username and password; credentials are stored as salted SHA‑256 hashes in a local SQLite database. After successful authentication the server issues a cryptographically secure session cookie named `session_id`. The service provides the following operations:

1. **Login** – verifies credentials and establishes a session.
2. **Profile View** – displays the authenticated user’s name and bio in an HTML page.
3. **Profile Edit** – accepts a new bio via POST and updates the database.
4. **Admin Profile View** – allows a user with role `admin` to view any user’s profile page.

Key security boundaries:
- Only the owning user may read or modify their own profile; admins may view any profile but cannot edit others.
- User‑supplied bio content is preserved and rendered; it must be properly escaped in HTML to prevent client‑side script execution.
- All database updates are performed using parameterized queries to eliminate SQL injection risk.

### Functional Requirements
- **Login**
  - Accept `POST /login` with form fields `username` and `password`.
  - Verify the password against the stored salted SHA‑256 hash.
  - On success, generate a random session token, store it in a server‑side session map keyed by the token, and set an `HttpOnly` and `Secure` cookie named `session_id`.
  - Return a JSON response `{ "status": "ok" }`. On failure, return `{ "status": "error", "message": "invalid credentials" }`.
- **Profile View**
  - Accept `GET /profile` requiring a valid `session_id` cookie.
  - Retrieve the authenticated user’s record (`id`, `name`, `bio`, `role`) from the SQLite database.
  - Render an HTML page that includes the user’s `name` and `bio`. Escape both values with `html.escape` before embedding in the template.
  - Return HTTP 200 with `Content-Type: text/html`.
- **Profile Edit**
  - Accept `POST /profile/edit` requiring a valid `session_id` cookie.
  - Read a form field `bio` from the request body.
  - Verify that the session’s user ID matches the target user record (admin users cannot edit others’ bios).
  - Update the `bio` column in the database using a single parameterized statement:  
    `cursor.execute("UPDATE users SET bio = ? WHERE id = ?", (bio, user_id))`.
  - Return HTTP 200 with a confirmation message in JSON.
- **Admin Profile View**
  - Accept `GET /profile/<user_id>` where `<user_id>` is a numeric path component.
  - Decode and validate the `session_id` cookie; authorize only if the session’s role is `admin`.
  - Retrieve the requested user’s `id`, `name`, and `bio` using a parameterized query.  
    `cursor.execute("SELECT id, name, bio FROM users WHERE id = ?", (user_id,))`.
  - Render an HTML page with the requested user’s `name` and `bio`, escaping both with `html.escape`.
  - Return HTTP 200 or HTTP 403 if the caller is not an admin.
- **Session Management**
  - Sessions expire after a configurable timeout (e.g., 30 minutes) and are removed on logout.
  - All incoming requests verify the session cookie and reject missing or invalid tokens with HTTP 401.

### Constraints
- Use only Python standard library modules (`http.server`, `sqlite3`, `hashlib`, `secrets`, `http.cookies`, `html`, `time`, `json`, `urllib.parse`).
- Keep the entire implementation in a single `.py` file.
- Perform at most one database write operation per request.
- All user‑supplied text that appears in the HTML response must be escaped with `html.escape` to prevent XSS.
- All database updates and selects that involve user input must use parameterized queries to prevent SQL injection. 
- The session cookie must be set with `HttpOnly` and `Secure` flags. 
- Passwords are stored as salted SHA‑256 hashes; salting is performed with a per‑user random 16‑byte salt. 
- The application must not read or write any files outside the current directory. 
- Network access beyond serving HTTP requests is disallowed. 
- The solution must be deterministic and executable in a standard Python 3.11 environment.