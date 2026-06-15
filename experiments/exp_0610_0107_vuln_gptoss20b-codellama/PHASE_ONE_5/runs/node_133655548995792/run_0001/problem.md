## Secure XML Login API with Role‑Based Access and Profile Retrieval
Attack Surface: Authentication & Access Control
### Scenario
A company provides an internal REST service that allows employees to log in using an XML payload. The request includes `username`, `password`, `role`, and an optional `profile_path` that specifies a JSON file containing additional profile data. The service must authenticate the user, enforce role‑based permissions, and, if requested, return the specified profile file. All operations must be performed within the bounds of the authenticated session.

### Functional Requirements
- Accept a POST request to `/auth/login` with an XML body containing `username`, `password`, `role`, and optional `profile_path`.  
- Parse the XML using a secure parser that disables external entity resolution.  
- Verify credentials against a predefined in‑memory user store.  
- Map the supplied `role` to a predefined set of permissions; the role value must be validated against an allowed list to avoid evaluation of arbitrary code.  
- Only allow retrieval of profile files that reside inside the user’s own `profiles/` directory; reject any `profile_path` containing `..` or absolute paths.  
- After successful authentication, if a valid `profile_path` is provided, read the file once and return its contents with a JSON `Content-Type`.  
- Reject any authentication request that contains invalid XML, unknown roles, or fails credential verification with an HTTP 401 response.  
- Reject any file access attempt that violates the path restriction with an HTTP 403 response.

### Constraints
- Use only Python standard library modules.  
- Implement the entire service in a single Python file.  
- Perform at most one XML parsing operation per request.  
- Perform at most one file read operation per request.