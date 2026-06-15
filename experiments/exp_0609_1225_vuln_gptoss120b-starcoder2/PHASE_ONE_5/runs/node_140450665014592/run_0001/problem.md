## Internal Markdown Report Publisher  
Attack Surface: Storage & Filesystem  

### Scenario  
A company intranet allows authenticated employees to publish internal reports written in Markdown. The employee uploads a Markdown file, selects a target category, and the system stores the file, converts it to HTML, and makes the resulting page available for download via a secure link. Because the upload endpoint is reachable from the company's web UI, the implementation must also protect against cross‑site request forgery.

### Functional Requirements  
- Verify that the request originates from a user whose session includes a valid CSRF token; reject any request lacking the correct token.  
- Authenticate the user and ensure they have the “EMPLOYEE” role before proceeding.  
- Accept a file upload named `report.md` via POST.  
- Store the uploaded file only inside the server‑controlled `uploads/` directory.  
- Validate that the filename contains only alphanumeric characters, hyphens, underscores, and ends with `.md`. Reject any filename that includes path separators, `..`, or null bytes.  
- Resolve the absolute path for the stored Markdown file under `uploads/`, ensuring the final path cannot escape that directory.  
- Convert the Markdown content to HTML using a standard library or safe third‑party parser that does **not** enable raw HTML input.  
- After conversion, encode any user‑supplied data that will appear in the generated HTML (e.g., headings, links) to prevent reflected or stored XSS.  
- Save the resulting HTML file under the `reports/` directory with the same base name but a `.html` extension, again enforcing path confinement to that directory.  
- Provide a GET endpoint that returns the generated HTML file with `Content-Type: text/html` and a `Content-Disposition: inline` header.  
- Return clear error responses for missing or invalid CSRF tokens, authentication failures, filename validation failures, path validation failures, Markdown parsing errors, or encoding issues.

### Constraints  
- Use only Python standard‑library modules (or a well‑maintained pure‑Python Markdown library) and avoid external services.  
- Implement the entire workflow in a single Python file (roughly 20–80 lines of code).  
- Perform exactly one file‑read for the uploaded Markdown and one file‑write for the generated HTML per request.