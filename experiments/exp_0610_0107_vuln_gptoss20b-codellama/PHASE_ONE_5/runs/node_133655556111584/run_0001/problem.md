## User Profile Image Fetcher Attack Surface: Storage & Filesystem
### Scenario
A web application serves user profile images stored on the server. The `/avatar` endpoint receives a query parameter `user_id` and is expected to read the image file from the `avatars/` directory located relative to the application root and return it as a response. The endpoint must ensure that only files within the `avatars/` directory are accessed, rejecting any input that attempts to traverse directories, use absolute paths, or otherwise escape the intended storage area.

### Functional Requirements
- Accept a `user_id` query parameter from an incoming HTTP GET request.  
- Resolve the file path by combining the `avatars/` directory with the sanitized `user_id` value and the `.png` extension.  
- Ensure that the resolved path is a descendant of the `avatars/` directory (no symbolic‑link escapes, no `..` components, no leading slashes).  
- Read the file from disk and return it with the appropriate `Content-Type: image/png` header.  
- If the file does not exist or the path resolution fails the request must return a 404 response.  
- All I/O must use a single file‑read operation per request.

### Constraints
- Use only Python standard library modules.  
- The implementation must reside entirely in a single `.py` file.  
- Do not perform any network or external service calls.  
- The solution must not read or write any files outside the `avatars/` directory.  
- The code should handle Unicode input safely and reject null bytes in the `user_id`.  
- The solution must be compatible with Python 3.8+.