## User Record Retrieval API
Attack Surface: User Inputs & Data
### Scenario
A web service exposes a `/api/records` endpoint that accepts a JSON payload containing `user_id` (integer) and `search` (string). Authenticated clients use the API to fetch records that belong to the specified `user_id`. The service must ensure that the requester is only able to query for their own `user_id`, validate the input data, and safely interact with the underlying SQLite database to retrieve matching records.

### Functional Requirements
- Accept a POST request to `/api/records` with `Content-Type: application/json`.
- Parse the request body and extract `user_id` and `search`.
- Verify that the authenticated session’s user ID matches the supplied `user_id`; otherwise, respond with HTTP 403 Forbidden.
- Validate that `user_id` is a positive integer and that `search` is a non‑empty string no longer than 200 characters containing only printable ASCII characters (no null bytes or control characters); otherwise, respond with HTTP 400 Bad Request.
- Execute a parameterized SQL query: `SELECT * FROM records WHERE user_id = ? AND data LIKE ?`, replacing the placeholders with the validated `user_id` and a `%search%` pattern.
- Return the result set as a JSON array in the response body with a 200 OK status.
- For any validation or authorization failure, return an appropriate error code and a concise error message.

### Constraints
- Use only Python’s built‑in `http.server` and `sqlite3` modules.
- Keep the implementation in a single Python file.
- Perform at most one database read operation per request cycle.
- Do not store or log any untrusted input beyond the immediate request handling.