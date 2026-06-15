## File Upload Validator with Dynamic Template Rendering
Attack Surface: User Inputs & Data

### Scenario
A web application offers a `/upload-template` endpoint that allows authenticated users to upload a custom HTML email template. The uploaded file is sent as a multipart/form‑data field named `template`. The server must store the file and later render it with user‑provided data to generate personalized emails. Implement the upload handler so that it safely parses the incoming file, validates its content to prevent inclusion of external entities, and ensures that any placeholder expressions inside the template are evaluated in a restricted manner before storage.

### Functional Requirements
- Accept a POST request with a multipart/form‑data payload containing the `template` file upload.
- Verify that the uploaded file has a `.html` extension and its size does not exceed 100 KB.
- Parse the file content and reject any document that contains a DOCTYPE declaration, external entity references, or XML processing instructions.
- Identify placeholder expressions delimited by `{{` and `}}` inside the HTML. Each expression must be a simple arithmetic or attribute lookup (e.g., `{{ user.age }}` or `{{ 5 + 3 }}`).
- Evaluate each allowed expression using a safe evaluator that does not permit function calls, imports, or access to built‑ins beyond basic arithmetic and attribute access on a predefined `user` dictionary.
- Replace the placeholders with the evaluated results and store the resulting HTML in the server’s `templates/` directory using a sanitized filename derived from the original upload name.
- Return a JSON response containing the stored filename and a success status.
- Respond with a 400 error if the file type, size, XML entity usage, or expression validation fails.

### Constraints
- Use only Python standard library modules.
- XML/HTML parsing must be configured to disable external entity processing.
- Expression evaluation must avoid direct use of `eval` on raw user content; employ an `ast`‑based whitelist or similar safe mechanism.
- Implement the entire functionality in a single Python file without external service calls.