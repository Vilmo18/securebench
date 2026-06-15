## XML‑Based Login Handler  
Attack Surface: Authentication & Access Control

### Scenario
A web service provides a `/api/login` endpoint that accepts an XML document containing a `<username>` and `<password>` element. The service parses the XML, extracts the credentials, validates them against an in‑memory user store, and on success creates a session token that is returned to the caller. Implement the handler so that the XML parsing is safe from external entity processing, and all received XML data is validated for well‑formedness and required elements before any authentication logic is performed.

### Functional Requirements
- Accept an HTTP POST request with a body containing an XML document.
- Parse the XML without allowing external entity resolution.
- Verify that the document contains exactly one `<username>` and one `<password>` element; reject any request missing these elements or containing additional unexpected nodes.
- Trim whitespace from the extracted values and ensure they are non‑empty strings.
- Authenticate the supplied credentials against a predefined dictionary of username‑password pairs.
- On successful authentication, generate a cryptographically random session token and return it in a JSON response `{ "session_token": "<token>" }`.
- On failure (invalid XML, missing elements, empty values, or bad credentials), return a JSON error response with an appropriate HTTP status code.

### Constraints
- Use only Python’s standard library modules.
- The entire implementation must reside in a single file and be no more than 80 lines of code.
- Perform exactly one parsing operation per request and one token generation operation on successful login.