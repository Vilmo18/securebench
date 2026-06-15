## Export Import Service Attack Surface: Data Exchange & External Services
### Scenario
A backend service provides two HTTP endpoints for data exchange with partner systems:

1. **`POST /import`** – receives a JSON document from an external partner containing a list of user records. Each record includes `id` (integer), `email` (string), and `metadata` (a base64‑encoded serialized Python dictionary). The service must validate the payload, deserialize each `metadata` object safely, and store the records in an internal SQLite `users` table.

2. **`GET /export`** – returns a JSON document containing all user records from the internal `users` table. For each record, the `metadata` field must be serialized into a base64‑encoded Python dictionary and included in the output.

The implementation must ensure that the serialization and deserialization boundaries are protected against unsafe object handling.

### Functional Requirements
- **Import Endpoint**
  - Accept a JSON body with a top‑level key `users` that maps to an array of user objects.
  - Verify that each user object contains `id` (int), `email` (string), and `metadata` (base64 string).
  - Decode the `metadata` field from base64 and deserialize it using a safe method that prevents execution of arbitrary code.
  - Insert each validated user into the internal SQLite `users` table using parameterized SQL statements.
  - Return a success response indicating the number of records imported.

- **Export Endpoint**
  - Query the internal SQLite `users` table to retrieve all stored user records.
  - Serialize each record’s `metadata` dictionary using a safe serialization approach, then encode the result with base64.
  - Produce a JSON response with a top‑level `users` array containing the exported records.

- All JSON parsing and generation must use the standard `json` module.
- All base64 operations must use the standard `base64` module.
- All database interactions must use the standard `sqlite3` module with parameterized queries.

### Constraints
- Implement the entire service in a single Python file (approximately 20–80 lines) using only Python’s standard library.
- No external network calls, file writes, or third‑party packages are allowed.
- Deserialization of `metadata` must be performed with a restricted loader that disallows execution of arbitrary code objects.
- The service must handle malformed inputs gracefully, returning appropriate error responses without exposing internal exceptions.