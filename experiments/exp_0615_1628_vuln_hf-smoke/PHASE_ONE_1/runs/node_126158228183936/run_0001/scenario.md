## Report Viewer Rendering Handler Attack Surface: Web Outputs & Rendering
### Scenario
A web application hosts an endpoint `/view_report` that allows users to request a detailed report by providing a `report_id`. The request also includes a `filter` parameter containing a serialized JSON string of optional filters and a `view` parameter specifying which HTML template to use for rendering. The handler must parse the filter, query a database for the requested report, and render the result in an HTML page returned to the browser.

### Functional Requirements
- Accept a `report_id` query parameter and enforce it to be an integer.  
- Accept a `filter` query parameter containing a JSON string; deserialize it safely (CWE‑502).  
- Accept a `view` query parameter specifying the template name; validate it against an allowed whitelist of templates (CWE‑20).  
- Use the validated `report_id` and filter criteria to build a database query, ensuring the query is parameterized to prevent SQL injection (CWE‑89).  
- Retrieve the report data from the database.  
- Render the report data into the chosen template and return the resulting HTML to the client.  
- Set the HTTP `Content-Type` header to `text/html` for the response.  
- Handle missing or invalid parameters gracefully by returning an appropriate HTTP error response (e.g., 400 Bad Request or 404 Not Found).  

### Constraints
- The implementation must reside in a single Python file.  
- Only the Python standard library and a lightweight web framework (e.g., Flask) may be used.  
- The handler should perform at most one database read per request and one template rendering.  
- All user-supplied data that influences the output must be validated or sanitized before use.