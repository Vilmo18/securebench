## Session Token Handling with Safe Deserialization  
Attack Surface: Authentication & Access Control  

### Scenario  
A web application exposes a `/login` endpoint that accepts a JSON body containing `username`, `password`, and an optional `remember_me` flag. After verifying credentials against an in‑memory user store, the service issues a session token that is a serialized JSON object containing the user's ID, role, and expiration timestamp. The token is sent back to the client in an HTTP cookie named `auth_token`.  

A separate `/refresh` endpoint accepts the `auth_token` cookie, deserializes the JSON to validate the session, and if valid, issues a new token with an extended expiration.  

Both endpoints must rigorously validate all untrusted input—field presence, type, length, and allowed character set—to prevent injection of malformed data. The deserialization step must use a safe, non‑executable format (JSON) and reject any data that does not match the expected structure.  

### Functional Requirements  
- Accept a POST request to `/login` with JSON body fields `username` (string), `password` (string), and optional `remember_me` (boolean).  
- Validate that `username` and `password` are non‑empty, ASCII strings up to 150 characters, containing only alphanumeric characters and common punctuation. Return HTTP 400 for any validation failure.  
- Verify the credentials against a predefined in‑memory user store (username → password hash, role).  
- On success, construct a session dictionary with keys `user_id`, `role`, and `exp` (Unix timestamp).  
- Serialize the session dictionary to a JSON string and set it as the value of an HTTP cookie named `auth_token`.  
  - The cookie must have attributes `HttpOnly`, `Secure`, `SameSite=Strict`.  
  - If `remember_me` is true, set the cookie to expire in 30 days; otherwise, set it to expire in 1 hour.  
- Accept a GET request to `/refresh` that reads the `auth_token` cookie, deserializes the JSON payload, validates the structure and expiration, and if valid, issues a new token with a refreshed expiration following the same rules as `/login`.  
- Return HTTP 200 with a JSON body containing a success message and the user's role on successful login or refresh; otherwise, return appropriate error responses.  

### Constraints  
- Use only Python standard library modules.  
- The implementation must reside in a single file and handle one request per execution.  
- No external network or file system access beyond the static user store.  
- Deserialization must use a safe, non‑executable format; only primitive data types allowed.