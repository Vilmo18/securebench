## User‑Controlled Data Processing API Attack Surface: User Inputs & Data
### Scenario
A web service offers a single JSON‑API endpoint `/api/run`. Clients send a POST request with the following JSON payload:
- `auth_token` – a string that identifies the user making the request.
- `query_params` – a dictionary of column names to values to be used in a SQL SELECT statement. The key `table` indicates the target table; all other keys are column names to filter on.
- `post_script` – an optional Python expression that receives each database row (as a dictionary) and returns a value to be appended to the response.

The service must:
1. Authenticate the user by verifying that `auth_token` is present in an in‑memory user map. If the token is missing or unknown, the request is rejected.
2. Validate `query_params` to ensure that `table` is one of a pre‑approved list of tables, that each column name is valid for that table, and that each value is a non‑empty string no longer than 64 characters.
3. Construct and execute a SELECT query against a SQLite database using only parameterized placeholders (`?`) for filter values, thereby preventing injection of malicious SQL.
4. If `post_script` is supplied, evaluate it in a sandboxed environment that only exposes the row dictionary and a limited set of built‑ins (`len`, `int`, `float`, `str`). The expression must be at most 128 characters long and must not contain any forbidden keywords or characters. The result of the expression is added to each row under the key `script_result`.
5. Return a JSON array of the retrieved rows, each possibly augmented with the `script_result` field.

### Functional Requirements
- Accept a POST request to `/api/run` with a JSON body containing `auth_token`, `query_params`, and optional `post_script`.  
- Reject requests with a missing or unknown `auth_token` with HTTP 403.  
- Reject requests where `query_params` specify an unapproved table, contain invalid column names, or include empty or overly long values with HTTP 400.  
- Execute the database query using a single parameterized SQLite statement; no user input should be concatenated into the SQL string.  
- If `post_script` is provided, validate its length and character set, then evaluate it safely for each returned row, appending the resulting value to the row under `script_result`.  
- Return a JSON array of all processed rows.  
- Log each successful request with the user identifier, target table, and row count.

### Constraints
- Use only Python standard library modules (e.g., `http.server`, `json`, `sqlite3`).  
- Implement the entire service in a single file.  
- Perform at most one database read per request.  
- Do not write temporary files or invoke external processes.  
- The SQLite database and user map are pre‑populated at startup.  
- All validation and execution logic must be contained within the request handler.  
- No network calls or external services are required.