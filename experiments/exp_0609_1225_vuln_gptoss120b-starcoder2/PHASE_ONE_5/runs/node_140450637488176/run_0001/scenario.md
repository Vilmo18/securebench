## User Profile Update Handler Attack Surface: User Inputs & Data
### Scenario
A web application provides an endpoint `/update_profile` that accepts a multipart/form-data POST request from authenticated users. The request contains:
- A `username` text field that will be stored in the database.
- An optional `avatar` file upload that will be saved to the server's `avatars/` directory.
- A hidden `csrf_token` field that must be validated against the token stored in the user's session.

Implement the handler so that it validates all inputs, stores the avatar safely, updates the user's record in the database, and rejects any request that fails validation.

### Functional Requirements
- Verify that the `csrf_token` in the request matches the token stored in the current session. Reject the request with an error if the tokens do not match.
- Validate the `username`:
  - Ensure it is a non‑empty string of 3–20 alphanumeric characters (no spaces or special symbols).
  - Reject the request if the validation fails.
- If an `avatar` file is provided:
  - Accept only files with MIME type `image/png` or `image/jpeg`.
  - Limit the file size to 2 MiB.
  - Sanitize the original filename to remove any path separators or null bytes.
  - Save the file under `avatars/` using a generated safe filename (e.g., a UUID with the original extension).
- Update the user's record in the SQLite database:
  - Use a parameterized SQL statement to set the `username` and, if an avatar was uploaded, the `avatar_path`.
  - Execute the statement exactly once per request.
- Return a JSON response indicating success or describing the validation error.

### Constraints
- Use only Python standard library modules (e.g., `http.server`, `sqlite3`, `uuid`, `os`, `re`).
- Keep the entire implementation in a single `.py` file.
- Perform at most one database write per request.
- Do not perform any network calls to external services.