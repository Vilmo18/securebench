## Secure File Retrieval Command Handler  
Attack Surface: User Inputs & Data  
### Scenario  
A web service offers a `/retrieve` endpoint that accepts a query parameter `filename`. The endpoint runs a shell command to read the requested file from a protected `data/` directory and returns the file’s content as plain text. The implementation must safely handle the user‑supplied `filename` so that only files within `data/` are accessible and the command execution cannot be subverted.  
### Functional Requirements  
- Accept a `filename` query parameter from an HTTP GET request.  
- Resolve `filename` to an absolute path inside the server’s `data/` directory.  
- Reject any request that attempts directory traversal, uses absolute paths, or includes null bytes.  
- Execute the safe shell command `cat <resolved_path>` to obtain the file content.  
- Return the file contents in the HTTP response body with a `Content-Type: text/plain` header.  
- If the file does not exist or the request is invalid, return a `404 Not Found` response.  
- Ensure that the command is invoked in a way that the `filename` is not interpreted by the shell (e.g., use argument lists rather than shell string interpolation).  
### Constraints  
- Use only Python’s standard library modules.  
- Implement the entire handler in a single Python file.  
- Perform at most one shell command execution per request.  
- Do not write any temporary files or use external services.