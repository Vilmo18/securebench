## Config File Upload and Secure XML Parsing Attack Surface: Storage & Filesystem
### Scenario
An administrative web application exposes an `/admin/config/upload` endpoint that accepts a multipart form containing two fields: `filename` and `file`. The `filename` is the desired name to store the uploaded XML configuration file under the server-managed `config/` directory. After saving the file, the application immediately parses it with an XML parser to validate its contents before applying configuration changes. Both the file path handling and XML parsing must be securely implemented to ensure that only legitimate files are stored and that no external entity references can be resolved during parsing.

### Functional Requirements
- Accept a multipart/form request with `filename` (string) and `file` (file stream) fields.  
- Ensure the provided `filename`:
  - Is non-empty and contains only alphanumeric characters, underscores, hyphens, and dots.  
  - Does not contain directory separators (`/`, `\`) or any relative path components (`..`).  
  - Is limited to a maximum length of 255 characters.  
- Resolve the destination path as `config/<sanitized filename>` and write the uploaded file content to this location.  
- After writing, read the file back and parse it using an XML parser that prevents external entity resolution (e.g., by disabling DOCTYPE processing).  
- If parsing succeeds, consider the configuration valid; otherwise, reject the file and return an appropriate error response.  
- Return a success message on successful upload and parsing; return clear error messages for validation failures, file system errors, or parsing errors.  

### Constraints
- Use only Python standard library modules.  
- Keep the implementation in a single file.  
- Perform at most one file-write and one file-read operation per request.  
- Do not allow any other types of input beyond those specified.  
- Ensure the solution works on both Unix-like and Windows filesystems.