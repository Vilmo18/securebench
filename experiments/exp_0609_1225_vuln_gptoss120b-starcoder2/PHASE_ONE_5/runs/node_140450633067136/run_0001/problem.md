## Secure Import Service API Attack Surface: Data Exchange & External Services
### Scenario An internal analytics platform provides a `/api/import` HTTP POST endpoint that accepts a JSON payload from trusted partner services. The payload includes:
- `api_key`: a credential identifying the calling service.
- `file_path`: a relative path to a CSV file located in the server’s `data/imports/` directory.
- `search_term`: a value used to query the `records` table for matching entries.
- `user_note`: free‑text that will be included in the JSON response sent back to the caller.
- `transform_script`: a short Python expression intended to transform each CSV row before insertion.

Implement the endpoint so that it validates the caller, safely resolves the file, processes the CSV, executes the transformation in a restricted manner, performs a parameterized database lookup, and returns a JSON object containing the note and the query results.
### Functional Requirements
- Verify that `api_key` matches a known list of partner keys; reject the request with an error if the key is missing or unauthorized.
- Resolve `file_path` strictly within the `data/imports/` directory; reject absolute paths, parent‑directory references, or symbolic‑link indirections, and return an error for non‑existent files.
- Open the specified CSV file, read each row, and apply `transform_script` to produce a transformed row. The script must be evaluated without allowing import of modules, access to built‑ins, or execution of arbitrary statements.
- Insert the transformed rows into a temporary staging table using a parameterized SQL statement; do not concatenate `search_term` or any other user data into the query string.
- Perform a SELECT on the `records` table using `search_term` as a parameterized query argument, and include the result set in the response.
- Include `user_note` verbatim in the JSON response under the key `note`. Ensure the response format is valid JSON.
- Return HTTP status 200 on success and appropriate error codes for validation failures.
### Constraints
- Use only Python standard library modules (e.g., `json`, `csv`, `sqlite3`, `http.server`).
- Keep the entire implementation in a single file of roughly 20–80 lines.
- Perform at most one write to the database per request and one read from the CSV file.
- Do not invoke external processes or network services.