## XML Config Upload and Execution Attack Surface: Storage & Filesystem
### Scenario
A web application provides a `/config/upload` endpoint that allows any authenticated user to upload an XML configuration file. The uploaded file is stored in the server’s `configs/` directory using the original filename. After storing, the application automatically parses the file with Python’s `xml.etree.ElementTree`, which processes external entities, extracts the first `<eval>` element’s text, and executes that text with `eval()` to dynamically configure runtime behavior. The endpoint does not enforce any role checks before accepting the upload, and the stored file is read unconditionally for execution.
### Functional Requirements
- Accept a multipart/form‑data POST to `/config/upload` containing an XML file.
- Store the file under the configured `configs/` directory using the original filename.
- Read the stored file and parse it with `xml.etree.ElementTree.fromstring()`, allowing external entities.
- Locate the first `<eval>` element, retrieve its text content, and execute it with `eval()`; use the resulting object as part of the application’s configuration.
- Return an HTTP 200 response with a JSON body that includes the result of the evaluation.
- If the XML cannot be parsed, return an HTTP 400 response with an error message.
- No authentication or authorization checks are performed before storing the uploaded file.
### Constraints
- Use only Python standard library modules.
- The entire implementation must fit within a single Python file.
- The configuration directory path should be defined by a constant that can be modified at runtime.