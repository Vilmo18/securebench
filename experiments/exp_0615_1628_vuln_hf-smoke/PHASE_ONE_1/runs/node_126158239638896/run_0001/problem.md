## Secure User Profile Service with CSRF Protection  
Attack Surface: Authentication & Access Control  
### Scenario  
A lightweight web service offers three endpoints:  
- `POST /login` receives a `username` and `password`, validates them against an SQLite database, and creates an `HttpOnly` session cookie.  
- `GET /profile` displays the logged‑in user’s name and bio in an HTML page. The bio is user‑generated content and must be escaped before rendering to prevent script injection.  
- `POST /settings/update_email` allows an authenticated user to change their email address. The request must include a CSRF token that is tied to the user’s session; the token is generated when the profile page is rendered and verified before updating the database.

All database interactions use prepared statements, and any user‑controlled data shown in the HTML is escaped. The CSRF token is stored in the session and validated on POST.

### Functional Requirements  
- **Login (`/login`)**  
  - Accept a POST request with form fields `username` and `password`.  
  - Verify credentials against the `users` table (`id`, `username`, `password_hash`, `full_name`, `bio`, `email`) using a single prepared statement.  
  - On success, generate a cryptographically secure random session ID, store it in the `sessions` table (`session_id`, `user_id`, `expires_at`), and set it as an `HttpOnly` cookie.  
  - On failure, return a 401 Unauthorized response rendered as an HTML page with an error message.  

- **Profile (`/profile`)**  
  - Require a valid `SESSIONID` cookie that exists in the `sessions` table and has not expired.  
  - Retrieve the authenticated user’s `full_name`, `bio`, and `email` with a prepared statement.  
  - Render an HTML page that includes:  
    - The user’s full name inside an `<h1>` element.  
    - The user’s bio inside a `<p>` element, with all content escaped for HTML.  
    - A form for updating the email that includes a hidden `csrf_token` field.  
  - Return a 403 Forbidden response rendered as an HTML page if the session is missing, invalid, or expired.  
  - Return a 404 Not Found response rendered as an HTML page if the user record cannot be found.  

- **Email Update (`/settings/update_email`)**  
  - Require a valid `SESSIONID` cookie and confirm that the session exists and has not expired.  
  - Accept a POST request with form fields `new_email` and `csrf_token`.  
  - Validate that `csrf_token` matches the token stored in the session; if not, return a 403 Forbidden response rendered as an HTML page.  
  - Verify that `new_email` is a syntactically valid email address; if not, return a 400 Bad Request response rendered as an HTML page.  
  - Update the `email` column for the authenticated user using a prepared statement.  
  - Return a 200 OK response rendered as an HTML page confirming the update.  

### Constraints  
- Use only Python standard library modules (`http.server`, `sqlite3`, `http.cookies`, `secrets`, `time`, `html`, `re`).  
- Keep the entire implementation in a single `.py` file.  
- Perform at most one database query and one HTML rendering per request.