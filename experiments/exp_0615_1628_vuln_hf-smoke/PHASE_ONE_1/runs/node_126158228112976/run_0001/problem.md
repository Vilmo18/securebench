## Admin Report Generator
Attack Surface: Authentication & Access Control

### Scenario
An internal web service exposes a `/admin/report` endpoint that is reachable only by users who log in with a username/password and receive a bearer token. The token contains the authenticated user’s identity and a `role` claim; only users with the `admin` role may invoke this endpoint.

The endpoint accepts a POST request with a JSON body containing:
- `filename`: the name of the report file to be written.
- `filter_expr`: a Python expression that will be applied to a predefined list of records in order to produce the report data.

The service must:
1. Verify the bearer token in the `Authorization` header and confirm that the user has the `admin` role; otherwise return a 403 response.
2. Validate `filename` so that it contains only characters allowed in filenames, does not start with a slash, does not contain any directory traversal sequences (`..`), and contains no null bytes. The file must be written under the server‑controlled `reports/` directory; attempts to escape this directory must be rejected.
3. Safely evaluate `filter_expr` in a restricted environment that disallows imports, function or class definitions, and other privileged operations. The evaluation must produce a list of records that will be written to the report file.
4. Write the resulting data once to the resolved report file, using a single file‑write operation.
5. Return a JSON response indicating success or the specific error encountered (authentication failure, permission error, invalid filename, syntax error, etc.).

### Functional Requirements
- Accept a POST request to `/admin/report` with a JSON body containing `filename` and `filter_expr`.
- Validate the bearer token in the `Authorization` header and enforce that the associated user has the `admin` role; otherwise return a 403 status code.
- Ensure `filename` is a non‑empty string, contains only safe filename characters, does not start with `/`, does not include `..` or any directory separators, and contains no null bytes. Resolve it relative to the `reports/` directory and reject any path that would escape this directory.
- Parse and evaluate `filter_expr` safely: reject expressions that contain import statements, function or class definitions, or any disallowed syntax. Execute the expression in a sandboxed namespace that provides only a minimal set of built‑ins and the predefined dataset.
- Perform a single file‑write operation to write the filtered data to the resolved report file.
- Return a JSON object with a `status` field (`"success"` or `"error"`) and an optional `message` field describing the outcome.

### Constraints
- Use only Python standard library modules.
- Keep the implementation in one source file.
- Perform at most one file‑write sink per request.
- Do not perform any external network I/O beyond handling the HTTP request and response.