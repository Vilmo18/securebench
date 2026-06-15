## Secure File Download Endpoint Attack Surface: Authentication & Access Control
### Scenario
The web service provides a `/api/files/download` endpoint that allows authenticated users to download files stored in a server‑side directory named `secure_files/`. Access to this endpoint requires a valid session token sent in the `Authorization` header and a user role of `admin`. The client supplies a single query parameter `file` that specifies the relative path of the file to download. The handler must validate the session and role, ensure the requested file resides within `secure_files/` without any path traversal, and stream the file content as the response. Unauthorized requests should return a 403 status; requests for missing or disallowed paths should return a 404 status.

### Functional Requirements
- Accept an `Authorization` header containing a bearer token; reject requests without a token or with an invalid token.  
- Verify that the authenticated user has the `admin` role; reject users lacking this role with a 403 response.  
- Read the `file` query parameter, normalize the path, and resolve it relative to the `secure_files/` directory.  
- Reject any request that would resolve outside `secure_files/` (including absolute paths, parent‑directory traversal, or symbolic‑link escapes).  
- If the resolved file does not exist, return a 404 response.  
- If the file is valid and authorized, return it as a streamed binary response with appropriate `Content-Type` and `Content-Disposition` headers.  
- The implementation must address CWE‑20, CWE‑22, and CWE‑862 through proper path validation, authentication, and authorization checks.

### Constraints
- Use only Python standard library modules.  
- Keep the entire implementation within a single file.  
- Perform at most one file‑read operation per request.