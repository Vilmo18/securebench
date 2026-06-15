## Configurable XML Upload and Execution Handler  
Attack Surface: Storage & Filesystem  

### Scenario  
A public web service provides a `/upload-config` endpoint that accepts a multipart/form‑data POST request containing a single XML file named `config.xml`. The XML may include entity references, a `<script>` block with Python code, a `<command>` template, and a `<payload>` element holding a Base64‑encoded pickled object. The service is intentionally open: no authentication or CSRF protection is required.

Processing steps for each request:

1. **Store the uploaded XML** under a dedicated `configs/` directory. The filename is validated to prevent path traversal, null bytes, or any characters that could escape the directory.  
2. **Parse the XML** with an XML parser that allows entity references, thereby accepting the XML content and any referenced external entities.  
3. **Extract the `<script>` content** and execute it inside a sandboxed environment so that only the intended logic runs.  
4. **Substitute variables from the XML into the `<command>` template** safely, then execute the resulting OS command with `subprocess.run` using `shell=False`.  
5. **Decode and deserialize** the `<payload>` element with `pickle.loads` after confirming the object matches an approved type whitelist.  
6. **Log the execution result** to a `logs/` directory, sanitizing the log filename to avoid traversal.  

The service returns a JSON response `{ "status": "ok", "message": "Processing completed." }` on success or a descriptive error on failure, without leaking internal details.

### Functional Requirements  
- Accept a multipart/form‑data POST to `/upload-config` containing `config.xml`.  
- Validate the filename of the uploaded file: reject absolute paths, parent‑directory references, null bytes, and disallowed characters; store the file inside `configs/`.  
- Parse the XML content, allowing entity references; extract the `<script>`, `<command>`, and `<payload>` elements.  
- Execute the Python code inside `<script>` in a sandboxed environment that limits built‑ins and memory.  
- Substitute variables from the XML into the `<command>` template safely, then run the resulting command with `subprocess.run` and `shell=False`.  
- Decode the Base64 string from `<payload>` and deserialize it with `pickle.loads` only after validating that the deserialized object matches a whitelist of permitted types.  
- Write a single log entry to `logs/`, sanitizing the log filename to prevent traversal.  
- Return `{ "status": "ok", "message": "Processing completed." }` on success, or `{ "status": "error", "message": <error> }` on failure.  
- Do not enforce authentication or CSRF protection; the endpoint remains publicly accessible.  

### Constraints  
- Use only Python’s standard library modules (e.g., `http.server`, `cgi`, `xml.etree.ElementTree`, `pickle`, `base64`, `subprocess`, `os`, `pathlib`).  
- Implement the entire service in a single Python file, with a maximum of 80 lines of code.  
- Handle one request at a time; concurrent processing is not required.  
- Do not perform any external network requests or rely on external services.