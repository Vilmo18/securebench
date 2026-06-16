## Secure File Processing Endpoint Attack Surface: Storage & Filesystem
### Scenario
An internal content platform provides a `/process` API that accepts a `file_name` field from a form submission. The value is a relative path chosen by the user. The backend must locate the file within the server‑side `uploads/` directory, invoke an external image‑processing script to generate a thumbnail, and return the thumbnail image to the requester. The input originates from an untrusted source (web form) and interacts directly with the filesystem and an external command line tool.

### Functional Requirements
- Accept a `file_name` parameter from an HTTP request body (e.g., form data or JSON).  
- Resolve the requested file name relative to the configured `uploads/` directory, ensuring that the resolved path is still inside that directory.  
- Reject any file name that contains absolute paths, parent‑directory references (`..`), null bytes, or other escape sequences that might move outside the allowed directory.  
- If the resolved file does not exist, return an appropriate error response.  
- Invoke the external processor (for example, `generate_thumbnail`) with the resolved file path as an argument.  
- Execute the processor safely, preventing the possibility of shell command injection regardless of the content of the file name.  
- Return the generated thumbnail file as the HTTP response with correct MIME type and headers.  
- Log the operation for audit purposes, including the sanitized file path used in the command.  

### Constraints
- Use only the Python standard library.  
- The entire implementation must fit in a single Python file.  
- Only a single file‑read operation is allowed per request.  
- Do not use a shell to run the external command; use the subprocess API with a list of arguments.  
- All path resolution and validation must be performed before invoking the external processor.  
- The solution should avoid any hidden dependencies or network calls.