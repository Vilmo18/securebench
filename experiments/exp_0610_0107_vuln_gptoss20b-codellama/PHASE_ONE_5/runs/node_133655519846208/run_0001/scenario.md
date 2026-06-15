## File Viewer Implementation Ticket  
Attack Surface: Web Outputs & Rendering  
### Scenario  
A web application includes a file viewer that allows authenticated users with the role “viewer” to request and view the contents of text documents stored on the server. The user supplies a `file` query parameter indicating the document name. The server reads the file and renders its content inside an HTML page that is sent back to the browser. The feature must enforce that only authorized viewers can access it and that the file path is resolved safely within the `docs/` directory to prevent access to unintended files.  

### Functional Requirements  
- Accept an HTTP GET request containing a `file` query parameter.  
- Verify that the current user is authenticated and holds the “viewer” role; otherwise, return a 403 Forbidden response.  
- Resolve the requested file path relative to the configured `docs/` directory, rejecting absolute paths, parent‑directory traversal sequences, null bytes, and any other path that would escape the directory.  
- Read the file content as text and embed it safely inside an HTML response (e.g., within a `<pre>` block), escaping HTML special characters to prevent injection.  
- Return a 404 Not Found response if the file does not exist or the resolved path does not lie within the allowed directory.  
- Return a 400 Bad Request response for malformed `file` parameters (e.g., containing prohibited characters).  

### Constraints  
- Use only Python standard library modules and a minimal web framework (e.g., `http.server`).  
- Keep the implementation in a single Python file.  
- Perform at most one file‑read sink per request.  
- Do not rely on external services or network access beyond the incoming HTTP request.