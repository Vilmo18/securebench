## User Profile Viewer
Attack Surface: Web Outputs & Rendering

### Scenario
A web application provides a `/profile` endpoint that displays a user's profile page. The client sends a `username` query parameter. The service must retrieve the user's record from a relational database and render an HTML page that includes the user's display name, bio, and a list of their recent posts. All data shown on the page is visible to the browser. The implementation must handle the input safely, query the database correctly, and generate the HTML response without exposing internal errors.

### Functional Requirements
- Accept a `username` query parameter from the HTTP GET request.
- Retrieve the user record (`display_name`, `bio`) and up to ten recent posts (`title`, `content`) from the database using a parameterized query.
- Render an HTML page that includes:
  - A heading with the user's display name.
  - A paragraph with the user's bio.
  - An unordered list where each list item shows a post title in bold followed by its content.
- If the `username` does not exist, return a user‑friendly HTML page stating that the profile was not found.
- If any error occurs (e.g., database connection failure), return a generic error page without leaking stack traces or internal details.

### Constraints
- Use only Python standard library modules (e.g., `http.server`, `sqlite3`, `html` for escaping).
- Keep the entire implementation in a single Python file.
- Perform at most one database query per request.
- All dynamic data inserted into the HTML must be properly escaped to prevent script injection.