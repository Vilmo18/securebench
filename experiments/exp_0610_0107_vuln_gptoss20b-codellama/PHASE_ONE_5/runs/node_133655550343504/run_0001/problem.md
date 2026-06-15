## Template Management Service
Attack Surface: Storage & Filesystem
### Scenario
An internal web application provides a template repository that allows administrators to upload, view, and download template files. Uploaded templates are stored under a dedicated `templates/` directory on the server. A download endpoint serves requested templates back to clients. The service must enforce strict validation of template file names to prevent directory traversal or arbitrary file access.
### Functional Requirements
- Accept a multipart/form‑data POST request to `/templates/upload` containing a file and an optional description field.  
- Validate the submitted file name: it must match the regex `^[A-Za-z0-9_\-]+\.tpl$`, contain no directory separators, and be no longer than 128 characters.  
- Store the file inside the `templates/` directory using the validated name; reject the upload with a 400 response if validation fails.  
- Record the template name, upload timestamp, and uploader ID in a local SQLite database with a parameterized INSERT query.  
- Provide a GET endpoint `/templates/download?name=<file>` that retrieves the file name from the query string, validates it with the same rules, resolves the absolute path within `templates/`, and streams the file contents to the client with the `text/plain` MIME type.  
- Return a 404 response if the file does not exist or the name fails validation.  
- Log each upload and download attempt with timestamps and user identifiers.  
### Constraints
- Use only the Python standard library (e.g., `http.server`, `sqlite3`, `re`, `os`, `datetime`).  
- Keep the entire implementation in a single `.py` file.  
- Perform at most one file‑read operation per request.  
- All file operations must be confined to the `templates/` directory; no absolute paths or relative traversal should be allowed.  
- All database queries must be parameterized.  
- Enforce the file name validation rules strictly, returning clear error messages for invalid names.