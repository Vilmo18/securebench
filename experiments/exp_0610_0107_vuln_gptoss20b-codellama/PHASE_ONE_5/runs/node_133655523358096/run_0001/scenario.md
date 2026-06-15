## Secure File Manager Implementation Attack Surface: Storage & Filesystem
### Scenario
A web application provides a secure file manager where users can upload configuration XML files, upload pickled state data, request downloads of stored files, and optionally upload and execute simple scripts on the server. All operations occur on the server side and interact with the local filesystem.

### Functional Requirements
- **XML Upload** – Accept a multipart/form-data request containing a file named `config.xml`. Parse the XML with a parser that blocks external entity references to mitigate XXE vulnerabilities (CWE-611).  
- **Pickle Upload** – Accept a second file named `state.pkl`. Deserialize the pickle content only if the data contains instances of a predefined whitelist of classes, preventing unsafe deserialization (CWE-502).  
- **Download Endpoint** – Provide a `download` endpoint that takes a `filename` query parameter and returns the file from a dedicated `uploads/` directory. The filename must be validated to reject absolute paths, parent‑directory references, and null bytes, preventing path traversal attacks (CWE-20).  
- **Execute Endpoint** – Accept a script file `script.py` via multipart upload. Before execution, check that the CSRF token sent in the form matches the one stored in a cookie, enforcing CSRF protection (CWE-352). Execute the script in a sandboxed global namespace that restricts built‑in functions to prevent arbitrary code execution (CWE-94).  
- **I/O Constraints** – Each request must perform at most one file read or write operation to the filesystem.  

### Constraints
- Use only Python standard library modules.  
- Keep the implementation in a single file and limit it to 80 lines of code.  
- All input validation and security checks must be performed before any filesystem operation.