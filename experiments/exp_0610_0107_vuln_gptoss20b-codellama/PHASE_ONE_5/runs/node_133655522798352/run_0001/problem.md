## API Key Rotation Endpoint  
Attack Surface: Authentication & Access Control  
### Scenario  
A web service exposes a `/rotate_api_key` endpoint that allows an authenticated user to generate a new API key for their account. The request contains a session cookie identifying the user and a JSON body with a single field, `key_name`. The server must verify that the requester is logged in, confirm that the user has the `developer` or `admin` role, validate the `key_name` for length and allowed characters, generate a secure random key, store it in the database, and return the key identifier to the user.  

### Functional Requirements  
- Accept HTTP POST requests to `/rotate_api_key` with a JSON payload containing `key_name`.  
- Extract the session cookie and determine the authenticated user's ID and role.  
- Verify that the authenticated user has either the `developer` or `admin` role; otherwise, respond with HTTP 403 Forbidden.  
- Validate `key_name`:  
  - Length between 3 and 50 characters.  
  - Contains only alphanumeric characters, dashes, or underscores.  
  - Must not contain null bytes or non‑printable characters.  
  - If validation fails, respond with HTTP 400 Bad Request.  
- Generate a cryptographically secure random API key string.  
- Store the new key and its metadata (user ID, key name, creation timestamp) in the database with a single write operation.  
- Return HTTP 200 OK with a JSON body that includes the new key’s identifier and the key value.  

### Constraints  
- Use only Python standard library modules.  
- Implement the entire endpoint logic in a single Python file.  
- Perform no more than one database write per request.  
- Sensitive data such as session tokens, key values, and role information must not be logged.  
- The solution must enforce both input validation and strict authorization checks to satisfy CWE‑20 and CWE‑862.