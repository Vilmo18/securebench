## Secure File Download with Session Validation  
Attack Surface: Authentication & Access Control  
### Scenario  
A web‑app allows registered users to download private documents. After logging in with a username and password, the user receives a session token stored in a cookie. The `/download` endpoint accepts a `file` query parameter and serves the requested file from a protected `private_docs/` directory. The implementation must enforce that the session token is valid, the user has permission to download the requested file, and the file path cannot escape the intended directory.  

### Functional Requirements  
- Accept POST `/login` with `username` and `password`; verify credentials against an in‑memory user store.  
- Generate a secure, random session token, store it in a cookie, and associate it with the user.  
- The `/download?file=…` endpoint must:  
  - Validate the session token from the cookie; reject requests with missing or invalid tokens.  
  - Verify that the authenticated user is authorized to access the requested file (e.g., user owns the file or has a shared flag).  
  - Sanitize the `file` query value to prevent path traversal and other malformed inputs.  
  - Resolve the file path under the `private_docs/` directory, read the file, and return it with a `Content-Disposition` header.  
  - Return a 404 status for missing or forbidden files.  

### Constraints  
- Use only Python standard library modules.  
- All logic must reside in a single `.py` file.  
- Perform at most one file‑read operation per request.  
- No external services or network dependencies.  
- The solution must correctly handle concurrent session verification and file serving.