## Secure Config Script Manager  
Attack Surface: Storage & Filesystem  
### Scenario  
An internal web service provides an administrator‑only API for handling server configuration scripts. The API supports the following operations:  

1. **Upload** a script file (.py or .sql) to a dedicated `config_scripts/` directory.  
2. **Download** an existing script from that directory.  
3. **Execute** a recently uploaded script on the server.  
4. **Search** configuration metadata stored in a local SQLite database.  

All endpoints require that the request be authenticated as an administrator before any action is taken.  

### Functional Requirements  
- **Authentication** – Verify that the request originates from an authenticated administrator (CWE‑862).  
- **File Upload**  
  - Accept a multipart/form‑data request containing a file named `script` with a `.py` or `.sql` extension.  
  - Store the file under `config_scripts/`, ensuring the file name cannot escape that directory (reject absolute paths, `..` components, and null‑byte injection).  
  - Enforce a 1 MB maximum size for uploaded files.  
- **File Execution**  
  - After a successful upload, allow the admin to trigger execution of the script.  
  - For Python scripts, run them via a subprocess with a restricted environment and capture the output.  
  - For SQL scripts, apply them to the SQLite database inside a transaction.  
  - Execute the subprocess call without a shell interpreter to avoid code‑injection risks (CWE‑94).  
  - Return the execution result or any error back to the caller.  
- **File Download**  
  - Serve a requested script only if it resides within `config_scripts/`.  
  - Return a 404 status for missing or disallowed files.  
- **Search Endpoint**  
  - Accept a query parameter `term`.  
  - Perform a lookup in the SQLite table `configurations` where `name` or `description` contains the term.  
  - Use a parameterized statement to prevent SQL injection (CWE‑89).  
  - Return matching records as a JSON array.  
- **Logging** – Log all upload, download, execution, and search actions with timestamps, the initiating admin’s identifier, and the action performed.  

### Constraints  
- Use only Python standard library modules.  
- Keep the implementation in a single `.py` file.  
- Perform at most one file‑I/O operation per request.  
- Do not invoke any external services or network connections.  
- The primary security boundary is the control of the `config_scripts/` directory path and file access.