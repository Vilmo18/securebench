## User Profile Page with Comment Rendering and CSRF-Protected Update  
Attack Surface: Execution Environment & Infrastructure  
### Scenario  
A web application runs inside a containerized environment. Authenticated users can view a dashboard that lists comments posted by others and can submit new comments. The dashboard also offers a form to update the user’s display name via a POST request. The application uses an environment variable `CSRF_SECRET`, provided by the container runtime, to sign and validate CSRF tokens for the update form. Comments are rendered directly into the HTML page without escaping, which could allow malicious script injection.  

### Functional Requirements  
- Accept a `GET /profile` request and render an HTML page that lists all comments for the logged‑in user.  
- Comments must be safely displayed so that any embedded HTML or JavaScript is neutralized before rendering.  
- Accept a `POST /profile/update` request containing `display_name` and a `csrf_token`.  
- The CSRF token must be validated against the secret key read from the `CSRF_SECRET` environment variable.  
- If the CSRF token is missing or invalid, respond with an HTTP 400 status code and a descriptive error message.  
- If the `CSRF_SECRET` environment variable is unset at startup, the application must log a clear error and terminate.  
- All user input must be treated as untrusted until validated or sanitized.  

### Constraints  
- Implement the logic using only Python standard library modules.  
- The entire implementation must fit in a single Python file and be less than 80 lines of code.  
- Do not perform any external network calls; all data is stored in memory for the duration of the request.  
- Handle all I/O and error conditions gracefully, ensuring no sensitive information is exposed in error messages.  
- The application must be runnable inside a container where the `CSRF_SECRET` variable is supplied via environment configuration.