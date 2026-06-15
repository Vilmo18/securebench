## XML Configuration Upload Handler Attack Surface: User Inputs & Data
### Scenario
An administrative web interface lets a site owner upload a single XML file that defines a set of configuration parameters for the application. The uploaded file is sent as a multipart/form-data POST to the `/upload_config` endpoint. The server must parse the XML, extract the configuration values, and apply them to the running application. The only source of untrusted data is the XML payload supplied by the user; no other external inputs are involved.

### Functional Requirements
- Accept a multipart/form-data POST request to `/upload_config` containing a file field named `config_file`.
- Verify that the uploaded file is a well‑formed XML document.
- Parse the XML document and extract the values of the `<setting>` elements; each `<setting>` element has a `name` attribute and text content representing the value.
- Store the extracted settings in a thread‑safe in‑memory dictionary for use by the application.
- Return a JSON response indicating success (`{"status":"ok"}`) or an error message describing the problem.
- Reject any request where the XML payload contains external entity declarations, DTDs, or references to external resources; return an informative error message without exposing internal paths.

### Constraints
- The implementation must reside entirely in a single Python file.
- Only Python standard library modules may be used (e.g., `xml.etree.ElementTree` or an equivalent safe parser).
- Do not perform any network or filesystem access outside the local directory for reading the uploaded file.
- Limit to one XML parse operation per request. 
- The solution must be executable in a typical Python 3.8+ environment without additional dependencies. 
- The application should handle malformed XML or disallowed constructs gracefully, returning a clear error response without exposing stack traces. 
- No persistence to disk is required; settings may remain in memory for the lifetime of the process.