## Secure Pipeline Configuration Manager Attack Surface: Storage & Filesystem  
### Scenario  
A data‑processing service allows administrators to upload XML configuration files that define a processing job. Each configuration file is stored in the `uploads/` directory. An administrator can trigger the job via the `/run` endpoint. The job may execute an external script and optionally load a plugin module defined by the XML. Job output and execution logs are saved to the `logs/` directory and can be downloaded via `/download`.

The application must enforce file‑system boundaries, proper authorization, and safe handling of external inputs to prevent accidental or malicious file‑system access, command execution, code injection, and XML external entity processing.

### Functional Requirements  
- **Upload Endpoint (`/upload`)**  
  - Accept an XML file via multipart/form‑data.  
  - Store the file under `uploads/` using a unique, sanitized filename.  
  - Reject uploads containing XML external entities or other disallowed content.  
  - Return a JSON response containing the stored filename.  

- **Run Endpoint (`/run`)**  
  - Accept a query parameter `config=<filename>`.  
  - Verify the requester has an `admin` role; otherwise return HTTP 403.  
  - Read the specified XML file from `uploads/` (perform a single file read).  
  - Parse the XML, extracting:  
    - `script_path` – a path to an executable script.  
    - `arguments` – an optional list of arguments.  
    - `plugin_module` – an optional Python module name.  
  - Resolve `script_path` relative to the configured `scripts/` directory; reject absolute paths or parent‑directory traversal.  
  - Execute the script safely with `subprocess.run` (no shell) using the provided arguments.  
  - If `plugin_module` is specified, load the module from the `plugins/` directory using `importlib` and invoke its `process` function with the script output as input.  
  - Capture stdout and stderr, write them to a new log file in `logs/` with a UTC timestamped filename, and return a JSON response containing the log filename.  

- **Download Endpoint (`/download`)**  
  - Accept a query parameter `file=<logname>`.  
  - Serve the requested log file from `logs/` as an attachment.  
  - Reject requests for files outside `logs/` (including traversal attempts) and return 404 for missing files.  

### Constraints  
- Implementation must be in a single Python file using only the standard library.  
- Path handling must prevent directory traversal and absolute path usage.  
- Command execution must avoid shell expansion; arguments are passed as a list.  
- XML parsing must disallow external entities and untrusted DTDs.  
- Each request must involve at most one file‑read operation.  
- All user inputs must be treated as untrusted.  
- Response status codes and messages should reflect successful or error conditions only.  

This scenario covers CWE‑94 (code injection via plugin execution), CWE‑862 (missing authorization for `/run`), CWE‑611 (XML external entity processing), and CWE‑78 (OS command injection).