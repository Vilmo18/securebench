## Secure File Download Handler
Attack Surface: Storage & Filesystem
### Scenario
A web service exposes a GET endpoint `/download` that allows authenticated users to retrieve files stored on the server. The client supplies a `file` query parameter that specifies the relative path of the desired file within a protected `files/` directory. The handler must resolve the requested path, ensure that the final target is strictly inside the `files/` directory, reject any attempt to traverse outside this directory, and return the file contents with the appropriate MIME type. Missing or disallowed paths must result in a 404 response.

### Functional Requirements
- Accept a GET request to `/download` with a `file` query parameter.  
- Resolve the requested file path relative to the configured `files/` directory.  
- Normalize the path and verify that it does not escape the `files/` directory (e.g., via `..` segments or absolute paths).  
- If the path is invalid or the file does not exist, return an HTTP 404 response.  
- If the path is valid, read the file contents once and return them as a binary response with the correct `Content-Type` header.  
- Do not expose any other files or directories outside the protected `files/` directory.

### Constraints
- Use only Python standard library modules.  
- Keep the implementation in a single file.  
- Perform at most one file-read operation per request.  
- Do not write any files to the filesystem.