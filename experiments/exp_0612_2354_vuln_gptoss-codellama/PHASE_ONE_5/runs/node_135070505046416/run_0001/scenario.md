## Secure Partner Data Import API  
Attack Surface: Data Exchange & External Services  

### Scenario  
A corporate platform offers a `/partner/import` endpoint that receives data from external partner services via HTTP POST. Each request contains an XML payload specifying a path to a file bundled with the partner’s data package. The platform must verify that the request comes from an authorised partner (CWE‑862), reject CSRF attempts (CWE‑352), parse the XML securely to avoid external entity injection (CWE‑611), and resolve the supplied file path in a way that prevents directory traversal (CWE‑22). The extracted file is then read once and forwarded to an internal processing queue. The service is expected to run without external network calls or reliance on third‑party libraries.  

### Functional Requirements  
- Accept a POST request to `/partner/import` with an XML body and mandatory authentication header.  
- Validate that the authentication token matches a pre‑registered partner ID; deny the request if the token is missing or invalid (Missing Permissions).  
- Require a CSRF protection token supplied in a custom header; reject the request if the token is absent or does not match the stored nonce for the partner.  
- Parse the XML payload using a parser that has external entities disabled to prevent XML External Entity attacks.  
- Extract a `<filePath>` element from the XML; resolve the path relative to a dedicated `partner_files/` directory; reject any path that attempts to traverse outside this directory.  
- Perform a single file read operation to obtain the content of the resolved file; if the file does not exist, return a 404 response.  
- Forward the file content to an internal message queue for downstream processing; do not write any data back to the filesystem beyond the single read.  
- Return a JSON response indicating success or the specific error (unauthorized, CSRF failure, XML parse error, traversal attempt, file missing).  

### Constraints  
- Use only Python standard library modules.  
- Keep the entire implementation in one file (≤80 lines).  
- Perform at most one file‑read sink per request.  
- Do not write to disk or perform external network calls during request handling.