## Customer Data Import API Attack Surface: Data Exchange & External Services
### Scenario
A SaaS platform provides a `/api/import` endpoint that accepts a JSON payload from partner services. The payload includes a `source_file` field indicating the relative path of a CSV file located in a shared import directory, a `sql_filter` string that will be used to filter records during a database query, and a `notes` field that may contain free‑form text. The service must read the specified CSV file, apply the SQL filter to retrieve matching rows from the `customers` table, and return an HTML snippet summarizing the results, embedding the `notes` content. Implement the endpoint so that it correctly validates inputs, safely constructs the database query, prevents directory traversal when accessing the CSV file, and safely renders the HTML output.

### Functional Requirements
- Accept a POST request with a JSON body containing `source_file` (string), `sql_filter` (string), and `notes` (string).
- Resolve `source_file` against a fixed `IMPORT_DIR` on the server, rejecting any attempts to escape this directory.
- Open and read the CSV file; if the file does not exist or is invalid, respond with a 400 error.
- Execute a parameterized SELECT query on the `customers` table using the provided `sql_filter` as a WHERE clause condition, ensuring the query cannot be manipulated to execute unintended SQL.
- Generate an HTML snippet that includes a table of the retrieved customer rows and displays the `notes` text.
- Return the HTML snippet with a `Content-Type: text/html` header.
- Return appropriate error responses for malformed JSON, missing fields, or validation failures.

### Constraints
- Use only Python standard library modules and the `sqlite3` module for database access.
- Keep the entire implementation in a single file.
- Perform exactly one file read and one database query per request.