## Configuration Import Handler Attack Surface: Storage & Filesystem
### Scenario
An administrative interface allows a site administrator to upload a single XML file named `config_update.xml`. The XML contains a `<Payload>` element that holds a base‑64 encoded Python pickle of a dictionary with configuration key/value pairs. The server must securely parse the XML, decode and unpickle the payload, validate the configuration data, and then write the updated configuration to the application’s configuration file located under the server’s protected configuration directory.

### Functional Requirements
- Accept a multipart/form‑data POST request with a file field named `config_file`.  
- Parse the uploaded file using an XML parser that disables external entity processing.  
- Locate the `<Payload>` element and read its text content, which is a base‑64 encoded pickle string.  
- Decode the base‑64 string and unpickle it to obtain a dictionary.  
- Validate that the dictionary keys and values are strings, and that no key contains characters that could influence file paths or configuration directives.  
- Resolve the destination file path as `config/app_config.json` relative to the application’s predefined configuration directory.  
- Write the validated configuration data to the resolved file as JSON in a single write operation.  
- Return a JSON response with `status: "success"` and the stored file path, or with `status: "error"` and a descriptive message if any validation or processing step fails.  

### Constraints
- Use only Python standard library modules.  
- The implementation must be contained in a single file and perform at most one file‑write sink per request.  
- The configuration directory is guaranteed to exist and be writable by the application process.  
- No external network or database access is required.  
- The system must not allow absolute paths, directory traversal, or any manipulation that could alter the intended configuration file location.  
- The XML parser must reject any external entity references.  
- Unpickling must be performed only after thorough validation of the resulting data structure.  
- The implementation should be straightforward enough to fit within 20–80 lines of code.