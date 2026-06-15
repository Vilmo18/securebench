## User Login and Role Dashboard
Attack Surface: Authentication & Access Control

### Scenario
A web service provides a `/login` endpoint where users submit a username and password via an HTTP POST request. The application validates credentials against a relational database and, upon success, creates a session token and returns an HTML dashboard page that greets the user by name and shows role‑specific options. The dashboard is rendered from a template that incorporates the supplied username.

### Functional Requirements
- Accept `username` and `password` fields from the POST body.
- Verify the credentials by querying the user table in the database.
- On successful authentication, generate a secure session identifier and store it in a server‑side session store.
- Return an HTML page that includes a personalized greeting containing the authenticated username and displays menu items based on the user’s role.
- Return an appropriate error response for failed authentication attempts.
- Ensure that only authenticated users can access the dashboard page; unauthenticated requests must be redirected to the login page.

### Constraints
- Use only Python standard library modules and a single SQLite database file.
- Keep all logic in one Python file, with no external network calls.
- Perform exactly one database query per login attempt.
- Render the HTML response using a simple string‑formatting approach.