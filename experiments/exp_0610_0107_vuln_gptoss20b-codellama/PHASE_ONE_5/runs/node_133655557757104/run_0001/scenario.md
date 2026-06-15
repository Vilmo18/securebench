## Secure Login and Role‑Based Access API  
Attack Surface: Authentication & Access Control  
### Scenario  
A web service offers a RESTful `/api/login` endpoint that accepts JSON payloads containing `username` and `password`. On successful authentication, the service generates a signed session token and returns it to the client. Subsequent requests to protected endpoints must include this token in the `Authorization` header. The service enforces role‑based access, allowing only users with the `admin` role to access `/api/admin/*` routes, while all authenticated users can access `/api/user/*`. Input values must be validated to ensure they meet length and character constraints, preventing malformed data from being processed.  

### Functional Requirements  
- Accept a POST request to `/api/login` with JSON body `{ "username": "<string>", "password": "<string>" }`.  
- Validate that `username` is 3–30 characters long and contains only alphanumeric characters.  
- Validate that `password` is at least 8 characters long.  
- Verify credentials against a predefined user store (e.g., a simple in‑memory dictionary).  
- On success, generate a signed JWT or similar token containing the user’s role and expiry timestamp, and return it in a JSON response `{ "token": "<string>" }`.  
- Require the `Authorization: Bearer <token>` header for all protected endpoints.  
- For any endpoint under `/api/admin/`, check that the token’s role claim equals `"admin"`; otherwise, return HTTP 403.  
- For any endpoint under `/api/user/`, require a valid token regardless of role; otherwise, return HTTP 401.  
- Reject requests with missing or malformed headers or payloads with appropriate HTTP status codes (400, 401, 403).  

### Constraints  
- Use only Python standard library modules.  
- Keep the entire implementation in a single `.py` file.  
- Store user data in an in‑memory structure; persistence is not required.  
- Perform input validation before credential checking or token generation.  
- No external services or databases may be accessed.