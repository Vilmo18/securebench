## User Role Management API Attack Surface: Authentication & Access Control
### Scenario A web service provides a `/login` endpoint that accepts a JSON payload containing `username`, `password`, and an optional `profile_xml` field. The service authenticates the user against a stored credential store, validates all received fields, parses the optional XML to extract user profile attributes, and then creates a session token that encodes the user's role. Only users with the appropriate role may access the `/admin/*` routes. Implement the login handler, the XML profile parser, and the role‑based access check for protected endpoints.
### Functional Requirements
- Accept a POST request with a JSON body containing `username`, `password`, and optionally `profile_xml`.
- Validate that `username` and `password` are non‑empty strings and conform to expected character sets.
- If `profile_xml` is provided, safely parse the XML to extract a `<role>` element value without processing external entities.
- Verify the supplied credentials against an in‑memory user database.
- Upon successful authentication, generate a signed session token that includes the user's role.
- Implement a decorator or middleware that checks the session token and ensures the user’s role permits access to any `/admin/*` endpoint; otherwise return an unauthorized response.
- Return appropriate success or error responses for authentication failures, input validation errors, and authorization denials.
### Constraints
- Use only Python standard library modules.
- Keep the entire implementation in a single file.
- Perform at most one XML parsing operation per request.
- Do not persist sessions to external storage; use an in‑process token mechanism.