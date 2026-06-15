## Admin Execution Endpoint Attack Surface: User Inputs & Data
### Scenario
A web service exposes a `/admin/execute` endpoint that allows a user with the “admin” role to perform three actions in one request:
1. Submit a single SQL query (`sql_query`) to be run against the application database.
2. Upload a configuration file (`config_file`) to be written under a predefined `configs/` directory.
3. Provide a short Python snippet (`python_code`) to be executed in a restricted environment.

The request is sent via POST and contains:
- A JSON body with `sql_query` and `python_code`.
- A multipart file field named `config_file`.
- A `session` cookie that carries a serialized session object indicating the user’s role.

The service must verify that the session indicates an “admin” role, validate all user‑supplied data, and safely process each payload before interacting with the database, executing code, or writing to disk.

### Functional Requirements
- Accept a POST request to `/admin/execute` containing the JSON body, multipart file, and `session` cookie as described.  
- Deserialize the `session` cookie securely; reject the request if the deserialized `user_role` is not “admin”.  
- Validate `sql_query` so that it contains only a single command, excludes disallowed keywords (e.g., `DROP`, `DELETE` without `WHERE`), and contains no null bytes or other disallowed constructs. Execute the validated query against the database using a parameterized statement.  
- Validate `python_code` to allow only safe operations: disallow imports, file I/O, and built‑ins that can affect the system. Execute the snippet in a sandboxed namespace with a limited set of built‑ins.  
- Sanitize the uploaded `config_file` filename, store it under `configs/`, and ensure that path traversal or overwriting of critical files cannot occur.  
- Return a JSON response that includes the result set of the SQL query, the exit status and stdout of the Python snippet execution, and the relative path where the uploaded configuration file was stored.

### Constraints
- Use only Python’s standard library modules.  
- Implement the endpoint in a single source file.  
- Perform at most one file‑write operation per request for the uploaded configuration file.