## Secure Admin Dashboard Access  
Attack Surface: Authentication & Access Control  
### Scenario  
A company intranet hosts an “Admin Dashboard” that is only visible to users with the `admin` role. The application accepts a username and password via an HTTPS POST request to `/login`. On successful authentication it issues a cryptographically secure session token stored in an HttpOnly, Secure cookie. Subsequent requests to `/admin` must validate the session token and confirm the user’s role. The dashboard retrieves system metrics from a SQLite database, loads a UI layout from `dashboard_layout.xml`, deserializes the admin’s preference file (`{username}_prefs.json`), and renders the page as HTML. All user‑controlled data must be handled safely before reaching the final output.

### Functional Requirements  
- Accept `username` and `password` via an HTTPS POST request to `/login`.  
- Verify credentials against the `users` table using a parameterized SQL query (protects against SQL injection, CWE‑89).  
- On successful login, generate a session token with `secrets.token_urlsafe()`, store it server‑side, and return it in an HttpOnly, Secure cookie.  
- Reject authentication failures with a generic error message.  
- For a GET request to `/admin`, validate the session token and confirm the `admin` role; otherwise redirect to `/login`.  
- Retrieve metric data from the `metrics` table using a parameterized SELECT statement.  
- Load the page layout from `dashboard_layout.xml` using `xml.etree.ElementTree`, configuring the XML parser to disallow external entities and DTDs (prevents XXE, CWE‑611).  
- Deserialize the admin’s preference file (`{username}_prefs.json`) with `json.loads()`; avoid binary deserialization (CWE‑502).  
- Render the dashboard as an HTML response, escaping all user‑supplied fields (e.g., metric names, preference values) before insertion into the template (prevents XSS, CWE‑79).  
- Return a 404 or appropriate error page if the admin layout file is missing or the user lacks the required role.

### Constraints  
- Use only Python standard library modules (`sqlite3`, `secrets`, `http.cookies`, `xml.etree.ElementTree`, `json`, etc.).  
- Implement the solution in a single Python file (≈ 20–80 lines).  
- Perform at most one file‑read sink per request (the XML layout file).  
- All database interactions must employ parameterized queries.  
- XML parsing must be configured to disallow external entities and DTD processing.  
- Deserialization of user data must use `json.loads()`; binary serialization formats are disallowed.  
- The session token must be cryptographically random and stored only server‑side.  
- The cookie must be set with HttpOnly and Secure attributes.  
- All rendered HTML must escape user‑controlled content.