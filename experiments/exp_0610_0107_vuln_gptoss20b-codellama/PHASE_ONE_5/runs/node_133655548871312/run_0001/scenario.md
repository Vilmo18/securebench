## Secure Admin Plugin Loader Attack Surface: Authentication & Access Control  
### Scenario  
An enterprise web application hosts an admin portal that exposes a `/admin/load_plugin` endpoint.  
- **Role:** The user must be an authenticated administrator, verified by a JWT bearer token supplied in the `Authorization` header.  
- **Input Source:** The endpoint accepts a multipart/form-data request containing a single file field named `plugin_config`. The file is an XML document describing a plugin.  
- **Data Handled:**  
  1. **XML configuration** – includes:  
     - `<script>`: a string of Python code to be executed on the server.  
     - `<sql_file>`: a relative path that points to a SQL script stored under a protected `plugins/sql/` directory.  
     - `<parameters>`: a list of key/value pairs that will replace placeholders in the SQL script.  
  2. **File system** – the SQL script referenced by `<sql_file>`.  
  3. **Database** – a local SQLite database (`app.db`).  
- **Requested Operation:**  
  1. Verify the admin token.  
  2. Parse the uploaded XML securely, disallowing external entity resolution.  
  3. Resolve `<sql_file>` against the `plugins/sql/` directory, preventing directory traversal.  
  4. Load the SQL script, perform placeholder substitution using the supplied `<parameters>`.  
  5. Execute the resulting query safely against the database.  
  6. Evaluate the `<script>` content using `eval` in a restricted namespace that contains only the database cursor and standard library modules necessary for the script.  
  7. Return a JSON response indicating success or detailed failure.  

### Functional Requirements  
- Accept a JWT token in the `Authorization` header; reject requests without a valid admin token.  
- Accept only an XML file in the `plugin_config` form field; reject other content types or missing files.  
- Parse the XML without resolving external entities or processing DTDs.  
- Resolve the `<sql_file>` path relative to a fixed `plugins/sql/` base directory; reject absolute paths, paths containing `..`, or any attempt to escape the base directory.  
- Read the referenced SQL file exactly once.  
- Substitute parameters via string replacement only for placeholders in the form `{{param_name}}`. Reject or sanitize any unsupported placeholder syntax.  
- Execute the final SQL statement using a parameterized query interface to the SQLite database.  
- Evaluate the `<script>` string with `eval` in a sandboxed dictionary that supplies only a `cursor` object and the `json` module; do not expose built‑ins or external modules.  
- Return a JSON payload `{ "status": "success" }` on successful completion or `{ "status": "error", "message": "<error description>" }` on failure.  

### Constraints  
- Use only Python standard library modules (e.g., `http.server`, `xml.etree.ElementTree`, `sqlite3`, `json`, `jwt`, `re`).  
- The entire implementation must reside in a single `.py` file.  
- Perform no more than two file‑read operations per request: one for the uploaded XML, one for the referenced SQL script.  
- The solution should not depend on external services or network access.  
- Keep the code concise (approximately 20–80 lines of Python).  
- The server should handle concurrent requests safely without shared mutable state.