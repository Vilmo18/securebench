## Role‑Based File Retrieval Service
Attack Surface: Authentication & Access Control

### Scenario
A web‑application provides an endpoint `/fetch` that allows authenticated users to retrieve configuration files needed for their role. Users log in with a username and password, receive a session token, and then request a file by name. The service reads a role‑to‑directory mapping from an XML configuration file, validates the requested file name, constructs the absolute path, checks that the user’s role permits access to that directory, and finally executes a system command to compress the file before sending it back.

### Functional Requirements
- Implement a login function that accepts `username` and `password`, validates them against a hard‑coded credential store, and returns a session token.
- Store the session token in a server‑side dictionary mapping tokens to user roles.
- Load a role‑to‑directory mapping from an XML file named `role_dirs.xml`. The XML may contain external entities.
- Provide a `/fetch` handler that accepts a `token` header and a `filename` query parameter.
- Validate the `filename` to ensure it contains only alphanumeric characters, underscores, hyphens, and a `.conf` extension.
- Resolve the file path by joining the directory associated with the user’s role (from the XML mapping) and the validated `filename`.
- Ensure the resolved path does not escape the role directory (prevent path traversal).
- Verify that the session token is present, valid, and that the associated role matches the directory being accessed.
- Compress the target file using a system command (e.g., `gzip`) and return the compressed data as the response.
- Return appropriate error responses for authentication failure, invalid input, unauthorized access, missing files, or any processing error.

### Constraints
- Use only Python standard library modules.
- Keep the entire implementation within a single Python file (approximately 20–80 lines of code).
- Perform exactly one file‑read and one command‑execution per request.