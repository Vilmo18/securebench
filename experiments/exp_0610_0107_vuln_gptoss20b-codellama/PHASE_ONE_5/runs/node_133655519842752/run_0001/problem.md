## Secure Report Viewer  
Attack Surface: Web Outputs & Rendering  
### Scenario  
An internal web portal hosts confidential reports in the server directory `secure_reports/`. Authenticated staff members request a specific report through the `/reports/view` endpoint by supplying a `report` query parameter. The endpoint must:  
- verify the user’s authentication status;  
- validate the supplied report name to prevent directory traversal and ensure only allowed file types are accessed;  
- stream the requested file to the browser with the correct MIME type.  
If the requested report is missing or the request fails validation, the endpoint should return a generic 404 error page that does not expose internal file system layout.  

### Functional Requirements  
- Accept a `report` query parameter from the incoming request.  
- Confirm the requester is authenticated; otherwise, respond with HTTP 401 Unauthorized.  
- Resolve the requested report name relative to the configured `secure_reports/` directory.  
- Validate that the report name contains only letters, digits, dashes, underscores, and ends with one of the allowed extensions: `.pdf` or `.html`.  
- Reject any path that would resolve outside the `secure_reports/` directory (e.g., containing `../`, absolute paths, or null bytes).  
- If the file exists and passes all checks, read it once and return its contents with the appropriate `Content-Type` header (`application/pdf` or `text/html`).  
- If the file does not exist or fails validation, return an HTTP 404 Not Found response with a generic error message that omits internal file system details.  
- Log each access attempt, recording the user identifier, requested report name, and outcome (success or error).  

### Constraints  
- Use only Python standard library modules.  
- Implement the entire functionality in a single Python file.  
- Perform at most one file‑read operation per request.