## Dynamic Template Rendering Endpoint
Attack Surface: Web Outputs & Rendering
### Scenario
A web application exposes a `/render` endpoint that accepts a POST request containing a `payload` field. The payload is a Base64‑encoded pickled object supplied by the client. This object describes which template to render and the data to inject into that template. The endpoint must decode, deserialize, validate, and render the template, then return the resulting HTML to the browser.

### Functional Requirements
- Accept a POST request to `/render` with a `payload` form field containing a Base64‑encoded pickled object.
- Decode the Base64 data to obtain the raw pickle bytes.
- Deserialize the bytes into a Python object using the `pickle` module.
- Validate that the deserialized object is a dictionary with the exact keys `template` and `context`.
- Ensure `template` is a string matching one of the pre‑approved template names (`welcome`, `profile`, `report`).
- Ensure `context` is a dictionary mapping string keys to string values; reject any other types.
- Use the `string.Template` class to substitute the values from `context` into the chosen template.
- Return the rendered HTML with a `Content-Type: text/html` response.
- If any step fails (e.g., decoding, deserialization, validation, missing template), return an HTTP 400 response with an error message.

### Constraints
- Use only Python standard library modules; no third‑party packages are allowed.
- Implement the entire endpoint in a single Python file.
- Perform at most one file read or write operation per request. 
- The template files are stored in a server‑managed `templates/` directory; access only these files. 
- Do not expose internal file paths or stack traces in error responses.