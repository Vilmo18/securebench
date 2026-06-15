## Config Management Portal Attack Surface: Storage & Filesystem
### Scenario
A web‑based configuration portal allows authenticated administrators to upload XML configuration files, list stored configurations, and apply a selected configuration to the system. When applying a configuration, the server parses the uploaded XML, extracts parameters, builds an SQL statement to store the configuration in a local SQLite database, and dynamically generates a small Python module that implements helper functions based on the XML content. The portal must protect against unauthorized actions by requiring a CSRF token on state‑changing requests. All file paths, XML content, and generated code must be validated before use.

### Functional Requirements
- **Upload**: Accept a multipart/form‑data request containing an XML file named `config.xml`. Store the file under the directory `configs/` using a sanitized filename derived from the original name.
- **List**: Return a JSON array of the filenames of all stored configuration files in `configs/`.
- **Apply**: Receive a request with a `filename` parameter (the name of a stored configuration) and a valid CSRF token.  
  1. Load and parse the specified XML file.  
  2. Extract configuration values and use them to construct a parameterized INSERT statement into the local SQLite database.  
  3. Generate a Python module file `helpers/<sanitized_name>_helper.py` that defines functions based on the XML values. The generated code must be written safely to the filesystem.
- **CSRF Protection**: Every POST request (`upload` and `apply`) must include a `csrf_token` that matches the token stored in the user's session.
- **Responses**: Return appropriate HTTP status codes (200 for success, 400 for malformed input, 403 for invalid CSRF token, 404 for missing files, 500 for internal errors).

### Constraints
- Use only Python standard library modules.  
- All file system interactions must be confined to the `configs/` and `helpers/` directories.  
- Filenames must be validated to prevent directory traversal, null bytes, or other illegal characters.  
- XML parsing must be performed with external entity processing disabled.  
- SQL statements must be executed using parameterized queries.  
- Generated Python code must be written without executing arbitrary code from the XML.  
- The implementation must fit within a single Python file (approximately 20–80 lines of code).