## Session Token Validator
Attack Surface: Authentication & Access Control

### Scenario
A web service provides a `/login` endpoint that authenticates users and issues a signed session token. Clients present this token in subsequent requests via an `Authorization: Bearer <token>` header. The token is a base64‑encoded, JSON‑serialized object that includes the username and expiration timestamp. Implement the token verification routine that deserializes the incoming token, validates its signature, checks expiration, and extracts the username for access‑control decisions.

### Functional Requirements
- Accept an `Authorization` header containing a Bearer token.
- Decode the base64 payload and deserialize the JSON object.
- Verify the token signature using a server‑side secret key.
- Ensure the token has not expired (compare the timestamp to the current time).
- Return the extracted username to the caller if all checks pass; otherwise reject the request with an authentication error.

### Constraints
- Use only Python standard library modules.
- Keep the implementation in a single file.
- Perform exactly one deserialization operation per request.