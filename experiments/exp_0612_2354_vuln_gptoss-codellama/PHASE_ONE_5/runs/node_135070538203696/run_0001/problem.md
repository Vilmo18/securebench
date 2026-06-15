## User Profile Page Rendering Attack Surface: Web Outputs & Rendering
### Scenario
A web application serves a `/profile` endpoint that displays a user’s personal information (name, email, and mailing address). The request includes a `user_id` query parameter supplied by the client. Only the account owner or an administrator may view any user profile. The application retrieves the profile data from an in‑memory data store, renders it into an HTML template, and returns the page to the browser. If the requester is not authorized to view the requested profile, the application must return a standard 403 Forbidden page. If the specified `user_id` does not exist, a 404 Not Found page is returned.

### Functional Requirements
- Accept a `user_id` query parameter from the HTTP request.  
- Identify the currently authenticated user and their role (e.g., from a session cookie or token).  
- Verify that the authenticated user is either the owner of the requested profile (their `user_id` matches the requested `user_id`) or has an administrator role.  
- If the authorization check passes, retrieve the profile data for `user_id` from the data store.  
- Render the profile data into an HTML template and return the resulting HTML as the HTTP response.  
- If the authorization check fails, return a 403 Forbidden response with a user‑friendly error page.  
- If the specified `user_id` does not exist in the data store, return a 404 Not Found response with an error page.

### Constraints
- Implement the solution in a single Python file using only the Python standard library.  
- Use an in‑memory dictionary or a simple JSON file to simulate the data store; no external database or network access is required.  
- Perform rendering via string formatting or a minimal templating approach; do not use external templating libraries.  
- The code should perform at most one data‑store lookup per request.