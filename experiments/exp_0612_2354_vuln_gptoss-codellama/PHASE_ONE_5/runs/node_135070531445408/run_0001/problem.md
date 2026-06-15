## Partner Sync Webhook  
Attack Surface: Data Exchange & External Services  
### Scenario  
An external partner system posts JSON payloads to the `/partner/sync` endpoint to trigger either a database query or a file retrieval. The partner must provide a bearer token. The service must safely parse the JSON, enforce that only SELECT statements are executed, prevent path traversal when serving files, and return the requested data.  

Sample partner payloads:  
```json  
{ "task": "query", "sql": "SELECT id, name FROM users WHERE id = ?", "params": [42] }  
{ "task": "download", "file": "reports/annual_summary.pdf" }  
```  

### Functional Requirements  
- Accept a POST request to `/partner/sync` with a JSON body.  
- Verify the `Authorization` header contains a bearer token that matches a pre‑approved list; return HTTP 401 for missing or invalid tokens.  
- Parse the request body using a safe JSON parser from the Python standard library; return HTTP 400 for malformed JSON.  
- If `task` is `"query"`:  
  - Extract the `sql` string and an optional `params` list.  
  - Confirm that the `sql` string starts with the keyword `SELECT` (case‑insensitive) and contains no semicolons or additional statements.  
  - Execute the query against the database using a parameterized API to prevent injection.  
  - Return the result set as a JSON array with HTTP 200 status.  
- If `task` is `"download"`:  
  - Extract the `file` string.  
  - Resolve the requested file path relative to a fixed base directory `/srv/partner/files/` using safe path resolution to prevent traversal.  
  - If the resolved path is outside the base directory or the file does not exist, return HTTP 404.  
  - Return the file contents as a binary response with the appropriate MIME type and a `Content‑Disposition: attachment` header, with HTTP 200 status.  
- For any other `task` value, respond with HTTP 400 Bad Request.  
- Log each request, indicating the partner token, requested task, and outcome.  

### Constraints  
- Use only Python standard library modules.  
- Implement the entire service in a single `.py` file.  
- Perform at most one file read or database query per request.