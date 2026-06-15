## File Import and Cataloging Service
Attack Surface: Storage & Filesystem

### Scenario
A web‑based admin console allows authenticated staff to import CSV files containing product data. The staff selects a file from their workstation and uploads it via an HTTP POST to `/import`. The server saves the uploaded file to a configurable `imports/` directory, then records the file path and a user‑provided “source label” in a SQLite database for later processing. Implement the import endpoint so that files are stored safely, the stored path cannot escape the designated directory, and the database insertion handles the inputs correctly.

### Functional Requirements
- Accept a multipart/form‑data request with:
  - A file field named `data_file`.
  - A text field named `source_label`.
- Validate that `source_label` contains only alphanumeric characters, spaces, hyphens, and underscores.
- Save the uploaded file into the configured `imports/` directory using the original filename.
- Ensure the final storage path is confined to the `imports/` directory (no absolute paths, no `..` traversal, no null byte tricks).
- Insert a new record into the SQLite database table `imports_log` with columns `id` (auto), `file_path`, and `source_label`.
- Use parameterized queries for the database insertion.
- Return a JSON response `{ "status": "success", "file": "<saved_filename>" }` on success, or an appropriate error message on failure.

### Constraints
- Use only Python’s standard library (e.g., `http.server`, `sqlite3`, `os`, `pathlib`, `re`).
- Keep the entire implementation in a single file, between 20 and 80 lines of code.
- Perform exactly one file‑write operation and one database‑write operation per request.