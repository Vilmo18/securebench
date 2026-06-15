## Template Management Endpoint
Attack Surface: Storage & Filesystem

### Scenario
A content management system provides an `/admin/template` page where authenticated administrators can upload HTML template files that are stored on the server and later rendered as part of public pages. The upload form includes a hidden CSRF token that must be validated. The system also allows administrators to specify a Python helper module name (chosen from a predefined directory) that will be imported and used to process data before rendering the template.

### Functional Requirements
- Accept a multipart/form-data POST request with fields:
  - `csrf_token` – the CSRF protection token that must match the session value.
  - `template_file` – an HTML file uploaded by the administrator.
  - `helper_module` – the name of a Python module (without extension) located in the `helpers/` directory.
- Validate the CSRF token before processing any other input.
- Store the uploaded `template_file` under the `templates/` directory, preserving the original filename but rejecting any path traversal characters, absolute paths, or null bytes.
- Ensure the stored filename ends with `.html`; reject any other extensions.
- Import the specified `helper_module` from the `helpers/` directory using a safe import mechanism that does not allow execution of arbitrary code outside that directory.
- When rendering a public page, read the stored HTML template and apply the helper module’s `process(data)` function to the page data before insertion.
- Return appropriate success or error responses for each validation step.

### Constraints
- Use only Python standard library modules.
- Keep the entire implementation in a single file (approximately 20–80 lines of code).
- Perform at most one file‑write operation per upload request and one file‑read operation per page render.