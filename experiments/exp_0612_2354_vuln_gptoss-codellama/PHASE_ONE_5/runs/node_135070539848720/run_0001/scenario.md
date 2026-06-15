## Secure File Storage Service Attack Surface: Storage & Filesystem
### Scenario
An internal web service offers authenticated employees the ability to upload confidential PDF documents to a protected directory and later retrieve them by filename. The upload endpoint accepts multipart form data containing a file. The download endpoint accepts a filename query parameter. The service must enforce that only the uploader can download a file and that all file paths are confined to the designated storage directory. Absolute paths, path traversal, and symbolic link attacks must be prevented. Missing or forbidden files should result in an HTTP 404. The application should use only the Python standard library and run as a single file.
### Functional Requirements
- Expose two HTTP endpoints: `/upload` (POST) and `/download` (GET).  
- `/upload` accepts a file via multipart/form-data, validates it is a PDF, and stores it under a per‑user directory inside `uploads/`. The stored filename should be a unique UUID to prevent name collisions.  
- `/download` accepts a `file` query parameter, resolves it inside the caller’s subdirectory, and streams the PDF back to the client.  
- Reject requests that attempt to reference files outside the caller’s directory, such as paths containing `../`, absolute paths, or null bytes.  
- Ensure that only the authenticated user who owns the file can download it; other users receive a 404.  
- Return a 404 response for non‑existent files or invalid requests.  
- Include appropriate HTTP headers for secure PDF delivery (content type, content disposition).  
### Constraints
- Use only Python standard library modules (e.g., `http.server`, `cgi`, `os`, `uuid`).  
- The implementation must fit in a single file and contain no more than 80 lines of code.  
- No external services or network access beyond the local HTTP server.