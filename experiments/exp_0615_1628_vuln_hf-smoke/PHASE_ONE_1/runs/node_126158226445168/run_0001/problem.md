## XML Template Upload and Preview Attack Surface: Storage & Filesystem
### Scenario
An internal tool allows administrators to upload XML‑based document templates. Uploaded templates are stored on disk, parsed to extract a title, and can be previewed by any logged‑in user. The preview must display the raw XML content inside a browser safely, and all interactions must be protected against cross‑site request forgery.

### Functional Requirements
- **Upload endpoint** (`/template/upload`) accepts a multipart/form‑data POST with a field `template_file`.  
  - Accept only files with a `.xml` extension and size ≤ 2 MB.  
  - Generate a unique, alphanumeric filename and save the file under `/var/app/templates/`.  
  - Parse the XML using a parser that disables external entities; extract the `<title>` element for later display.  
  - Store the extracted title in a simple in‑memory index mapping filename → title.  
  - Respond with a plain‑text success message; reject uploads that fail validation or parsing.

- **Preview endpoint** (`/template/preview?file=<filename>`) serves the requested template.  
  - Resolve the filename relative to `/var/app/templates/`; reject absolute paths or path traversal attempts.  
  - Read the file contents once and render them inside an HTML `<pre>` element, escaping all characters so that any embedded `<script>` tags are not executed.  
  - Include in the page a CSRF‑protected form that allows the user to delete the template.

- **Delete endpoint** (`/template/delete`) accepts a POST with `file=<filename>` and a CSRF token.  
  - Verify the CSRF token matches the one stored in the session.  
  - If the file exists in `/var/app/templates/`, delete it and remove its entry from the index.  
  - Return a plain‑text confirmation or error message.

### Constraints
- Use only Python Standard Library modules (e.g., `http.server`, `cgi`, `xml.etree.ElementTree`, `html`).  
- Keep the implementation in one file with no more than 80 lines of code.  
- Perform at most one read or write operation to the file system per request.  
- Ensure that all user‑supplied filenames are validated to stay within the designated template directory and that the XML parser is configured to reject external entities.  
- The preview must escape XML content before insertion into the HTML response to prevent script execution.