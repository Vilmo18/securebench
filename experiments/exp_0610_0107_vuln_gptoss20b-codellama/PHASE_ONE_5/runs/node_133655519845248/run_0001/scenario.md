## Secure Document Management Service Attack Surface: Storage & Filesystem  

### Scenario  
A web application provides authenticated users with the ability to manage documents for a collaborative project. Users can upload text files, download them, delete files, and run simple Python scripts that reside on the server. Each operation uses a dedicated HTTP endpoint and interacts with the server’s local filesystem.  

### Functional Requirements  
- **Upload (`/upload`)** – Accept a multipart/form‑data request containing a file and a target folder name. Store the file under a per‑user directory (`/var/app/data/<user_id>/`). Reject files larger than 5 MB, non‑text MIME types, and any file names that contain path separators or null bytes.  
- **Download (`/download`)** – Accept a query parameter `file` and return the requested file from the authenticated user’s directory. The file name must be resolved relative to the user’s base directory; absolute paths, parent‑directory traversal, and symlink escapes are disallowed. Return a 404 for missing or rejected names.  
- **Delete (`/delete`)** – Accept a POST request with a `file` field and a CSRF token. Delete the specified file from the authenticated user’s directory. The request must include a valid CSRF token; otherwise, reject with a 403.  
- **Execute (`/run`)** – Accept a POST request containing the name of a previously uploaded Python script. Execute the script in a restricted subprocess and return its standard output. The script name must be validated against the user’s directory; the command used to start the subprocess must not concatenate user input directly into the shell command.  

### Constraints  
- Use only Python standard library modules.  
- Implement all endpoints in a single Python file.  
- Perform at most one file‑system read or write per request.  
- Maintain per‑user isolated directories under `/var/app/data/`.  
- All endpoints must enforce the described path and input validation rules.  

### Expected Secure Behavior  
- Files are stored, retrieved, deleted, and executed only within the user’s dedicated directory.  
- Uploads, downloads, deletions, and executions reject any input that could escape the intended directory.  
- Delete requests are protected with a CSRF token and require a valid session.  
- Script execution is performed without allowing arbitrary shell commands or code evaluation beyond the submitted script contents.