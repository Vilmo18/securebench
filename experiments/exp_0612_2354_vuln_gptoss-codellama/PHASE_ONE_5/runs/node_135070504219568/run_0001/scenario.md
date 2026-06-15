## Dynamic Report Generation Endpoint
Attack Surface: Web Outputs & Rendering
### Scenario
A web application exposes a `/generate_report` endpoint that accepts a JSON payload containing a `report_name`, a `template` string with placeholders, and a set of `parameters`. Only authenticated users with administrative privileges may invoke this endpoint. The service resolves the requested report name relative to a protected `reports/` directory, substitutes the placeholders with the supplied parameters, generates the report content through a shell command, and returns the generated report embedded in an HTML page to the client. The system must enforce authorization, validate and sanitize all inputs, construct shell commands securely, and safely render the final report content within the browser.

### Functional Requirements
- Accept a POST request to `/generate_report` with a JSON body containing the keys `report_name` (string), `template` (string), and `parameters` (object).
- Verify that the caller is an authenticated administrator; otherwise respond with HTTP 403.
- Resolve `report_name` within a designated `reports/` directory, rejecting absolute paths, parent‑directory traversal, and null bytes.
- Allow only a predefined set of placeholders in the `template`; reject any disallowed characters or patterns.
- Perform placeholder substitution using the supplied `parameters` without executing arbitrary code.
- Construct a shell command to create the report file (e.g., `echo "<processed_template>" > reports/<report_name>.txt`) by passing arguments to a subprocess in list form, avoiding direct string concatenation in the command.
- Execute the shell command via the standard library’s subprocess facilities.
- Read the generated report file and return its contents as part of an HTML response rendered to the client.
- If validation fails or the report generation encounters an error, return an appropriate HTTP error status with a clear, user‑friendly message.

### Constraints
- Use only Python standard library modules.
- Implement the entire endpoint logic in a single Python file.
- Perform at most one file‑read sink per request.
- Do not make external network requests or depend on external services.