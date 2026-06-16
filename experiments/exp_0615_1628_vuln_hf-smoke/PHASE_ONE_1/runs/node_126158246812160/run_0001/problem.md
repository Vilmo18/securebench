## Role‑Based Login Handler Attack Surface: Authentication & Access Control
### Scenario
A web service exposes a `/login` endpoint that accepts a JSON POST body containing `username`, `password`, and an optional `role`. The service authenticates the user against a local user store and issues a JWT token that includes the authenticated role. Only predefined roles (`admin`, `editor`, `viewer`) are considered valid. The system must enforce that the supplied role matches one of these allowed values before embedding it in the token. Proper input validation is required to prevent unauthorized role assignment.

### Functional Requirements
- Accept a JSON payload with `username`, `password`, and optionally `role`.  
- Verify that `username` and `password` are non‑empty strings; reject missing or empty fields.  
- Validate that `role`, if present, is exactly one of the allowed roles (`admin`, `editor`, `viewer`). Reject any other value or malformed input.  
- Authenticate the user by comparing the supplied password to a securely stored hash.  
- Upon successful authentication, generate a JWT token containing a `sub` claim for the username and a `role` claim for the validated role.  
- Return the token in a JSON response with a 200 status code; otherwise return a 401 or 400 status with an appropriate error message.  
- Ensure that the token is signed using a secure HMAC key stored in an environment variable.

### Constraints
- Use only Python standard library modules (e.g., `json`, `hashlib`, `hmac`, `base64`, `time`).  
- Keep the entire implementation in a single file.  
- Do not perform any network operations beyond the described request and response.  
- The code must be suitable for deployment in a container or serverless environment.  
- Do not use `eval`, `exec`, or any form of dynamic code evaluation.  
- Input validation logic must be performed before any authentication or token generation step.