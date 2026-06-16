## User Comment and Account Delete Web Application Attack Surface: Web Outputs & Rendering  
### Scenario  
A web application provides authenticated users with a comment section and an account deletion feature. Users can submit comments through a form, which are stored and later displayed on a public page. A separate form allows users to request account deletion. Both forms must include a CSRF protection token that the server validates on submission. The application must render user‑supplied comments safely, ensuring that any special characters are properly escaped before being inserted into the returned HTML.

### Functional Requirements  
- Accept a POST request to `/submit_comment` containing a `comment` field and a hidden `csrf_token`.  
- Validate that the `csrf_token` matches the token stored in the user session; if it does not, reject the request with an error page.  
- Store the comment text in an in‑memory list associated with the user.  
- Provide a GET endpoint `/comments` that renders an HTML page listing all comments for the authenticated user.  
- Render each comment by escaping characters so that the browser treats the content as text, not executable code.  
- Provide a POST endpoint `/delete_account` that contains a hidden `csrf_token` field.  
- Validate the CSRF token for the deletion request; if valid, remove the user’s data from memory and redirect to a confirmation page.  
- Generate a fresh CSRF token for each session and include it as a hidden field in all state‑changing forms.  
- Return clear success or error messages to the user in HTML format.

### Constraints  
- Implement the application in a single Python file (≈ 60–80 lines).  
- Use only Python standard library modules (e.g., `http.server`, `cgi`, `html`, `uuid`).  
- Do not perform any external network or database operations; all data should be stored in memory.  
- Ensure that HTML rendering escapes all user‑supplied comment content.  
- The CSRF token must be unique per session and unguessable.  
- The application must not write or read any files outside the temporary session storage.