## Plugin Upload and Execution Handler
Attack Surface: Storage & Filesystem
### Scenario
A content management system (CMS) provides a feature for users to extend the system by uploading small Python modules that add new rendering capabilities. Any user who is logged in can access the `/plugins/upload` endpoint. The endpoint receives two form fields: `plugin_name` (the desired filename) and `plugin_code` (the source code). Upon submission, the CMS must store the plugin file in the server‑managed `plugins/` directory and immediately load and execute it so that its registration logic becomes active. The system requires only authentication; there is no fine‑grained authorization to restrict which authenticated users may upload and execute plugins.

### Functional Requirements
- Accept form fields `plugin_name` and `plugin_code` from an authenticated request.
- Verify that `plugin_name` ends with the `.py` extension, contains no `/` or `\`, and does not include null bytes.
- Resolve the target path by joining the configured `plugins/` directory with `plugin_name`. Reject any path that resolves outside the `plugins/` directory (e.g., due to parent‑directory traversal).
- Store the provided `plugin_code` as a UTF‑8‑encoded file at the resolved path, overwriting any existing file with the same name.
- Dynamically import the newly stored module using the standard library (e.g., `importlib`), ensuring that the module’s top‑level code is executed so that plugin registration hooks run.
- Return a JSON response indicating success or an error message for validation failures or import errors.
- Log the upload event with the requester’s user identifier and the plugin filename.

### Constraints
- Use only the Python standard library.
- Implement the handler in a single `.py` file that can be executed directly.
- Ensure that the file write and module import are performed in a single request cycle.
- Do not expose any additional filesystem paths or allow arbitrary code execution beyond what the uploaded plugin provides.