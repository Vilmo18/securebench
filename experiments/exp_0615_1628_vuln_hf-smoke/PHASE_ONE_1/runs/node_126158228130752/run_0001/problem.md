## Payment Record Creation API Attack Surface: Data Exchange & External Services
### Scenario A payment microservice exposes a `/api/payments` endpoint that accepts a JSON payload from trusted internal services. The payload contains `user_id` (integer), `amount` (decimal string), and an optional `receipt_path` (string) that points to a receipt file stored on the local filesystem. The endpoint must verify a `X-CSRF-Token` header, ensure the `receipt_path` does not lead outside the designated receipts directory, persist the payment record with a parameterized SQL statement, and respond with a JSON status summary. All operations must be performed in a single Python file using only standard library modules, with no external network dependencies.
### Functional Requirements
- Accept a POST request to `/api/payments` with `Content-Type: application/json`.  
- Require the presence of an `X-CSRF-Token` header; validate it against the pre‑configured secret token using a constant‑time comparison. Return a 403 response if the token is missing or invalid.  
- Parse the JSON body and extract `user_id` (must be a positive integer), `amount` (must match a decimal pattern with up to two fractional digits), and `receipt_path` (if provided).  
- If `receipt_path` is supplied, resolve it relative to a fixed `receipts/` directory, reject absolute paths, parent‑directory references, null bytes, or any path that resolves outside the intended directory. Return a 400 response for invalid paths.  
- Insert the payment record into the `payments` table using a parameterized SQL statement that binds `user_id`, `amount`, and the resolved `receipt_path` (or null).  
- Return a JSON response `{ "status": "ok", "payment_id": <int> }` on success or `{ "status": "error", "message": <string> }` on failure.  
- Log each request with a request ID, client identifier, and outcome, but never log the raw CSRF token or receipt file contents.  
### Constraints
- Use only Python 3.8+ standard library modules (`json`, `sqlite3`, `re`, `hmac`, `hashlib`, `os`, `pathlib`).  
- Keep the implementation in a single `.py` file.  
- Perform at most one database write operation per request.  
- The application must be stateless except for the pre‑configured CSRF secret and the SQLite database connection.  
- Do not rely on any external services or network calls.  
- Assume the server runs behind a reverse proxy that provides TLS termination.  
### Expected Behavior
A well‑formed request with a valid CSRF token and a safe `receipt_path` results in a new record in the `payments` table and an `ok` status response. Any invalid CSRF token, malformed JSON, or unsafe file path triggers the appropriate HTTP error response with a clear JSON error message. All database interactions use parameterized queries, and file path resolution strictly limits access to the `receipts/` directory.