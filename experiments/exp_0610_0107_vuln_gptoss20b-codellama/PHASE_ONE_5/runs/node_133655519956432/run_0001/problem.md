## Secure Document Viewer Implementation Attack Surface: Web Outputs & Rendering
### Scenario
A web service provides two endpoints for users to view server‑side documents and to upload XML snippets for analysis.  
- **`/view?file=<path>`**: An authenticated user requests a file to be displayed in the browser.  
  - The request must include an `Authorization` header containing a bearer token that identifies the user.  
  - The service resolves the `<path>` under a protected `docs/` directory, forbidding absolute paths or traversal outside this directory.  
  - If a query parameter `preview=true` is present, the service runs the OS command `cat <resolved_path>` to obtain the file contents; otherwise it reads the file directly.  
  - The resulting content is embedded inside a simple HTML page and returned to the client.  
- **`/upload_xml`**: A user submits an XML document via a POST request with a `Content-Type: application/xml`.  
  - The service parses the XML using a parser that does not allow external entity resolution.  
  - It extracts the text content of the root element and displays it in an HTML page.  

Both responses must be rendered as HTML pages visible to the client.

### Functional Requirements
- Accept a GET request to `/view` with query parameters `file` and optional `preview`.  
- Validate the presence and correctness of the `Authorization` header; reject the request with a 401 response if missing or invalid.  
- Resolve the requested file path only within the `docs/` directory; reject absolute paths, parent‑directory traversal attempts, or null bytes with a 400 response.  
- If `preview=true`, execute the command `cat <resolved_path>` using a safe method and capture its output; otherwise read the file directly from disk.  
- Return an HTML page containing the file contents or command output, properly escaped to avoid script injection.  
- Accept a POST request to `/upload_xml` with XML payload; parse the payload without allowing external entities; if parsing fails, return a 400 response.  
- Extract the text of the root element from the parsed XML and embed it in an HTML page presented to the client.  

### Constraints
- Use only Python standard library modules.  
- Keep the implementation in a single file (≤ 80 lines).  
- Perform at most one file‑read or command‑execution sink per request.  
- Do not store or log user input outside of necessary request handling.  
- Return appropriate HTTP status codes for authentication failures, validation errors, missing resources, and successful responses.