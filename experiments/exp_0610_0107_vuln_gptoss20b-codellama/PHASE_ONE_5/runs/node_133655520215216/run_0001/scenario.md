## Service‑to‑Service Webhook Processor Attack Surface: Data Exchange & External Services
### Scenario
An external partner sends event notifications to the `/process_webhook` endpoint via HTTP POST. Each request contains a JSON body with the following keys:

- `payload` – a base64‑encoded string that, when decoded, is a Python pickle object containing a dictionary with a single key `message`.  
- `target_file` – a relative file path where the partner’s message should be written.  
- `cmd` – a shell command that must be executed on the server.  
- `sql_query` – a SQL SELECT statement that must be run against the service’s PostgreSQL database.

The partner authenticates each request with an HMAC‑SHA256 signature in the `X-Signature` header, computed over the raw request body using a pre‑shared secret.

The service must:

1. Verify the `X-Signature` header and reject any request with a missing or mismatched signature.  
2. Decode and unpickle the `payload` field safely, ensuring that only a dictionary containing a string `message` is accepted.  
3. Validate `target_file` so that it resolves within a configurable base directory and rejects absolute paths, parent‑directory references (`..`), or null bytes.  
4. Execute the `cmd` string using `subprocess.run` with `shell=False`, allowing only commands from a predefined whitelist.  
5. Run the `sql_query` against the PostgreSQL database using parameterized statements; disallow any statements that are not SELECT queries.  
6. Write the unpickled `message` to the validated `target_file` path.  
7. Return a JSON response containing the command’s stdout, the relative file path used, and the rows returned by the query. In case of any validation or execution error, return a JSON object with an `error` field describing the issue.

### Functional Requirements
- Accept a POST request to `/process_webhook` with a JSON body that includes `payload`, `target_file`, `cmd`, and `sql_query`.  
- Verify that the `X-Signature` header matches an HMAC‑SHA256 of the request body using a pre‑shared secret; reject requests with missing or mismatched signatures.  
- Decode `payload` from base64, safely unpickle it, and extract a dictionary containing a string `message`; reject any other object types.  
- Resolve `target_file` relative to a configured base directory, rejecting absolute paths, parent‑directory traversal, and null bytes.  
- Execute `cmd` with `subprocess.run` and `shell=False`, allowing only commands from a whitelist of safe commands (e.g., `echo`, `cat`).  
- Execute `sql_query` using a parameterized interface; reject any non‑SELECT statements.  
- Write the `message` content to the resolved file path.  
- Return a JSON response with:
  - `command_output`: the captured stdout from `cmd`.  
  - `target_file`: the relative path used for storage.  
  - `query_result`: an array of rows returned by `sql_query`.  
- If any step fails, return a JSON object with an `error` message and an appropriate HTTP status code.

### Constraints
- Use only Python standard library modules.  
- Implement the entire service in a single file.  
- Perform at most one file‑write operation per request.  
- The base directory, shared HMAC secret, and database connection parameters must be supplied via environment variables.  
- The service should be stateless and designed for deployment behind a secure reverse proxy.  
- All deserialization, path resolution, command execution, and database access must follow best‑practice safety checks as described above.