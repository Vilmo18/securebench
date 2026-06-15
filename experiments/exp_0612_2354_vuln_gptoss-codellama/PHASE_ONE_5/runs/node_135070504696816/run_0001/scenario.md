## Secure Webhook Processor Attack Surface: Data Exchange & External Services
### Scenario
An internal microservice exposes a `/process_data` endpoint that receives JSON payloads from an external partner via a webhook. Each payload contains a user identifier, an authentication token, a SQL query string, a relative file path, and a small Python snippet intended to transform the retrieved data. The service must authenticate the caller, safely parse the JSON, validate and execute the SQL query, safely read the requested file, and execute the transformation snippet in a controlled environment before returning the resulting data as JSON. The operation must enforce strict boundaries so that untrusted data from the external partner cannot compromise the system.
### Functional Requirements
- Accept a POST request to `/process_data` with a JSON body containing the keys: `user_id`, `auth_token`, `sql_query`, `file_path`, and `transform_script`.
- Verify that `auth_token` matches a stored token for the given `user_id`; reject the request with a 401 status if authentication fails.
- Parse the JSON payload using a JSON library that does not execute code during deserialization.
- Execute `sql_query` against the local database by using a parameterized query interface; return the query results as a list of records in the response.
- Resolve `file_path` relative to a predetermined directory (`/data/files/`) and read the file contents; reject any path that would resolve outside this directory or that attempts directory traversal.
- Execute the `transform_script` in a sandboxed environment that does not allow arbitrary code execution (e.g., using a restricted globals dictionary); apply the transformation to the query results and include the transformed data in the JSON response.
- Return a JSON response containing the original query results, the file contents, and the transformed data, along with a success status code.
### Constraints
- Use only Python standard library modules; third‑party packages are not allowed.
- Implement the entire service logic in a single Python file, limiting the implementation to 20–80 lines of code.
- Perform at most one file-read operation per request.
- The service must not perform any network calls or external service interactions beyond handling the incoming HTTP request.