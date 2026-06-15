## Secure Upload and Import Handler Attack Surface: Storage & Filesystem
### Scenario
An internal management portal provides an `/admin/upload` endpoint that allows an authenticated administrator to submit two files in a single multipart/form‑data request: a configuration file named `config.xml` and a user data file named `data.json`. The server stores the uploaded files in a dedicated directory `/var/app/uploads`. After saving, the application parses the XML configuration, deserializes the JSON payload, and updates runtime settings. Each request must include a CSRF token that matches the token stored in the user’s session.

### Functional Requirements
- Accept a multipart/form‑data POST request to `/admin/upload` containing:
  - `config.xml`: an XML configuration document.
  - `data.json`: a JSON payload with user data.
  - `csrf_token`: a token that must match the token stored in the user’s session.
- Validate that each uploaded filename is a simple base name; reject any that contain directory separators, absolute paths, or null bytes.
- Resolve the filenames under the upload directory `/var/app/uploads` and write each file to disk using a single write operation per file.
- Parse `config.xml` with an XML parser that has external entity and DTD processing disabled; extract the required configuration values and apply them to the application.
- Deserialize `data.json` with a JSON parser, validate that only the expected keys (`user_id`, `preferences`, `roles`) are present and that each value is of the correct type; reject any payload that does not conform.
- Return a `200 OK` response with a success message if both files are processed correctly; otherwise return an appropriate error status and message.
- Enforce CSRF protection: if the `csrf_token` does not match the session’s token, reject the request with a `403 Forbidden` status.

### Constraints
- Use only Python standard library modules (e.g., `http.server`, `cgi`, `json`, `xml.etree.ElementTree`).
- All logic must reside in a single Python file and not exceed 80 lines of code.
- The upload handler may perform at most one file‑write operation per uploaded file.