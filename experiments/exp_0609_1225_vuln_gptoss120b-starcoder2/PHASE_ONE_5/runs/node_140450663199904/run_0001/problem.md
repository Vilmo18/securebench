## User Configuration Management Attack Surface: Storage & Filesystem
### Scenario
An internal admin portal provides a `/config/upload` endpoint that accepts a configuration file from an authenticated administrator. The file is stored in a dedicated `configs/` directory and later read by a scheduled job that loads the configuration into the application. Implement the upload handler and the configuration loader, ensuring that only authorized administrators can invoke them and that the stored file is safely deserialized before use.
### Functional Requirements
- Verify that the request originates from an authenticated administrator before processing the upload.
- Accept a file upload named `config_file` via a multipart/form‑data POST request.
- Restrict uploaded files to the `configs/` directory; reject any attempt to specify paths outside this directory.
- Store the uploaded file with a sanitized filename that removes directory traversal characters.
- Implement a function that reads the stored configuration file and deserializes its contents using a safe method that does not allow execution of arbitrary code.
- If deserialization fails or the file is missing, the loader should raise an appropriate error.
### Constraints
- Use only Python’s standard library.
- Keep the entire implementation in a single file, not exceeding 80 lines.
- Perform exactly one filesystem read operation when loading a configuration.