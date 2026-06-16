## User Feedback Submission Handler  
Attack Surface: User Inputs & Data  
### Scenario  
The web application exposes a `/feedback` endpoint that accepts an HTTP POST request containing two form fields: `comment` (the user's feedback text) and `username` (an optional nickname). The handler must store the feedback in a relational database and then render a confirmation page that echoes the submitted comment back to the user.  

The goal is to correctly handle the untrusted input from the form: validate and sanitize it for database insertion (avoiding SQL injection) and for HTML rendering (avoiding cross‑site scripting).  

### Functional Requirements  
- Accept a POST request to `/feedback` with form fields `comment` (required) and `username` (optional).  
- Ensure `comment` is a non‑empty string no longer than 500 characters; reject otherwise with an appropriate error response.  
- If `username` is supplied, validate it as an alphanumeric string up to 30 characters; reject otherwise.  
- Store the feedback in a table named `feedback` with columns `id`, `username`, `comment`, and `submitted_at`.  
- Use parameterized SQL statements to insert the data into the database, preventing injection attacks.  
- After insertion, render an HTML confirmation page that displays the sanitized `comment` and, if provided, the `username`.  
- Escape any HTML special characters in `comment` and `username` before rendering to protect against XSS.  
- Return a 200 OK status with the confirmation page on success, or an appropriate error status for validation failures.  

### Constraints  
- Use only Python standard library modules (e.g., `http.server`, `sqlite3`, `html`).  
- The implementation must reside in a single Python file and be executable without external dependencies.  
- Perform no more than one SQL query per request.  
- Do not perform any network or external service calls.  
- The application must run in a standard Python 3.x environment.