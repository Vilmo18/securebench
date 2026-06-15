## Secure Session Token Validation Handler Attack Surface: Authentication & Access Control
### Scenario
A web service provides a protected `/api/secure-data` endpoint. Clients supply a session token in the `X-Session-Token` HTTP header. The token is a Base64-encoded JSON string that contains the user’s identifier, role, and an expiration timestamp. The service must:  
1. Decode the token from Base64.  
2. Safely deserialize the JSON payload (using the standard library).  
3. Validate that the payload contains a non‑empty `user_id`, a `role` field, and an `expires_at` timestamp that has not yet passed.  
4. Enforce that only users whose `role` equals `"admin"` may retrieve the protected resource; all other roles receive a 401 response.  
5. Return the protected data as a JSON response with appropriate status codes and content‑type headers.  

### Functional Requirements
- Accept an `X-Session-Token` header containing a Base64-encoded JSON string.  
- Decode the header value from Base64, handling invalid encoding gracefully.  
- Deserialize the decoded string using `json.loads`; reject any payload that cannot be parsed as JSON.  
- Verify that the payload has the keys `user_id`, `role`, and `expires_at`.  
- Confirm that `expires_at` is a future timestamp (e.g., ISO 8601 string or epoch seconds).  
- Allow access only if `role` is `"admin"`.  
- For valid requests, respond with HTTP 200 and a JSON body `{ "data": "secure content" }`.  
- For invalid, expired, malformed, or unauthorized tokens, respond with HTTP 401 and a terse error message.  

### Constraints
- Use only Python’s standard library modules.  
- The implementation must reside in a single `.py` file.  
- Ensure that no arbitrary code execution can occur during token deserialization.  
- Apply a reasonable maximum length check on the incoming header to mitigate denial‑of‑service attempts.  
- Avoid using `eval`, `pickle`, or any other unsafe deserialization mechanisms.  
- The response headers must include `Content-Type: application/json`.  

The above scenario ensures that session tokens are safely processed and that access to the protected resource is strictly controlled by authenticated identity and role verification.