## User Document Download Service Attack Surface: Storage & Filesystem
### Scenario
The internal portal provides a `/download/document` endpoint that allows authenticated employees to retrieve personal and shared documents stored on the server. The request includes a query parameter `doc_id` that references a document record in the database. Each document record contains the relative path to the file within the `documents/` directory.

The handler must:

1. Verify that the requester is authenticated and has permission to access the requested document.  
2. Resolve the file path stored in the document record, ensuring that the final path is confined to the `documents/` directory.  
3. Open the file in binary mode and stream its contents back to the client with appropriate `Content-Type` and `Content-Disposition` headers.  
4. If the file does not exist, is outside the allowed directory, or the user lacks permission, return a 404 response.  

Implement the download service so that storage path control and filesystem access are handled securely.

### Functional Requirements
- Accept a GET request with a `doc_id` query parameter.  
- Retrieve the document record from the internal store and obtain the relative file path.  
- Resolve the absolute path and confirm it resides within the configured `documents/` directory.  
- Verify the authenticated user’s permission to access the document before reading the file.  
- Return the file content with correct MIME type and a `Content-Disposition: attachment` header.  
- Respond with a 404 status code for missing files, unauthorized access, or path violations.

### Constraints
- Use only Python’s standard library modules.  
- All file operations must be performed with paths resolved relative to the application’s root directory.  
- The entire implementation must be contained in a single Python file (approximately 20–80 lines).  
- No external network calls or third‑party services are permitted.