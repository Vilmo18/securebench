## Dynamic Plugin Configuration Loader Attack Surface: Storage & Filesystem
### Scenario A web application allows site administrators to add new plugins by uploading a configuration file. The uploaded file must be a JSON document that defines the plugin’s metadata and entry point. The server stores each uploaded file in a dedicated `plugins/` directory. On application startup, the system reads every file in that directory, deserializes its contents, validates the required schema, and registers the plugin. The implementation must prevent arbitrary code execution and ensure the upload and storage process is safe.
### Functional Requirements
- Accept an uploaded file with a `.json` extension from an authenticated administrator.
- Validate that the file contains only UTF‑8 encoded JSON data; reject binary or non‑JSON content.
- Store the file under the configured `plugins/` directory, ensuring that the file name cannot be used to escape the directory (no `../` or absolute paths).
- On application startup, iterate over all files in `plugins/`, read each file once, and deserialize its contents using `json.loads`.
- Verify that each deserialized object contains the keys `plugin_name`, `main_class`, and `version`; discard or log any file that does not conform.
- Register each valid plugin by importing the specified entry point; do not use `pickle`, `eval`, or any unsafe deserialization method.
- Return appropriate success or error responses for the upload process, and log any deserialization or validation failures.
### Constraints
- The implementation must be contained in a single Python file that uses only the standard library.
- The code should perform at most one file-read operation per plugin configuration file.
- The solution must be no longer than 80 lines of code.