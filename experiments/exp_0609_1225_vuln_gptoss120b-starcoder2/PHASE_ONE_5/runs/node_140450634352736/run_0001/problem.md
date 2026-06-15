## Customer Data Import API
Attack Surface: Data Exchange & External Services

### Scenario
A SaaS platform provides a `/api/import` endpoint that accepts JSON payloads from partner services. The payload contains a `sql_filter` string used to filter records, a `notes` field that will be displayed in a web dashboard, a `template_path` indicating a server‑side HTML template to apply, and a `requester_role` identifying the partner's permission level. Implement the endpoint so it processes the import safely while respecting the platform’s access policies.

### Functional Requirements
- Parse the incoming JSON request body.
- Validate that `requester_role` is one of `"viewer"` or `"admin"`; only `"admin"` may specify a custom `template_path`.
- Use the `sql_filter` value in a SELECT statement against the internal `customers` SQLite database, employing parameterized queries to avoid injection.
- Store the `notes` value and later render it in an HTML dashboard; ensure any content rendered to the dashboard cannot break the page structure or introduce scripts.
- Resolve `template_path` relative to the fixed `templates/` directory; reject absolute paths, parent‑directory traversal sequences, and any attempt to escape the directory.
- Return a JSON response containing the number of imported records and a status message.

### Constraints
- Use only Python standard library modules.
- Keep the implementation within a single Python file (≈20–80 lines).
- Perform a single database query per request.
- All input validation and sanitization must occur before any database, file system, or HTML rendering operations.