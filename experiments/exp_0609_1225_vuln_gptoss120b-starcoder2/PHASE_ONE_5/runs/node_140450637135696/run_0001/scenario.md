## Configurable Report Generator  
Attack Surface: Storage & Filesystem

### Scenario
A web‑based reporting tool allows authenticated administrators to upload a JSON configuration file that describes a custom report (title, column definitions, and optional inline Python expressions for computed columns). The service stores each uploaded file under a dedicated `configs/` directory, then reads the file, deserializes it, and generates an HTML report saved to `reports/`. The generated HTML is later served to end‑users. Implement the upload and generation workflow while respecting the storage boundaries and handling all inputs safely.

### Functional Requirements
- Accept a multipart/form‑data request with a file field named `config`. The request must include a valid CSRF token named `csrf_token`.
- Validate that the uploaded file:
  - Has a `.json` extension and a MIME type of `application/json`.
  - Is no larger than 100 KB.
  - Contains well‑formed JSON that conforms to the required schema (string `title`, array `columns`, optional `calc` objects).
- Store the uploaded file under `configs/` using a sanitized, unique filename (e.g., a UUID). Reject any path elements that could escape the directory.
- Deserialize the JSON using a safe method that does not execute arbitrary code.
- When processing the `calc` objects, ensure any inline expressions are evaluated in a restricted environment that prevents execution of unsafe code.
- Generate an HTML report using the data from the configuration. Escape all dynamic content inserted into the HTML to prevent script injection.
- Save the generated report as `reports/<sanitized‑filename>.html` inside the `reports/` directory. The filename must be derived from the stored configuration filename and must not allow directory traversal.
- Return a JSON response containing the URL of the generated report on success, or an appropriate error message on failure.

### Constraints
- Use only Python standard library modules.
- Keep the entire implementation in a single file (≈20–80 lines of code).
- Perform exactly one file‑write operation for the uploaded configuration and one for the generated HTML per request.
- No network calls or external services may be used.