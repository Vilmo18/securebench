## Secure Configuration File Manager  
Attack Surface: Storage & Filesystem  

### Scenario  
An internal web service provides administrators with the ability to upload, view, download, archive, and delete configuration files that reside in a dedicated `configs/` directory on the server. The service runs under a user account that has read/write privilege only to this directory. All filesystem interactions are strictly confined to `configs/`; no path outside this directory may be accessed.  

### Functional Requirements  

| Operation | Inputs | Expected Behavior | Validation | Security Mitigations |
|-----------|--------|-------------------|------------|---------------------|
| **Upload** | Multipart form containing a file | Store the file in `configs/` under its original filename | Resolve the target path inside `configs/`; reject uploads that use absolute paths, null bytes, or directory‑traversal sequences. | |
| **View** | Query parameter `filename` (publicly accessible) | Return the file contents as plain text. | Return HTTP 404 if the filename is missing, empty, or resolves outside `configs/`. | |
| **Download** | Query parameter `filename` (publicly accessible) | Return the file with a `Content-Disposition: attachment` header for download. | Return HTTP 404 if the filename is missing, empty, or resolves outside `configs/`. | |
| **Backup** | Form field `filename` | Verify the file exists in `configs/`. Execute a safe shell command (e.g., `tar -czf backup_<timestamp>.tar.gz <file>`) to create a compressed archive of the specified file, returning the command’s exit status and output. | Verify the file’s canonical path is within `configs/`. | |
| **Delete** | Requires an authenticated session and a valid CSRF token. Form field `filename` | Verify the file exists in `configs/`, delete it, and return a JSON success message. | Return an error if the session is missing, the CSRF token is invalid, or the file is not located inside `configs/`. |  

### Constraints  
* Use only Python 3 standard library modules.  
* Implement the entire service in a single `.py` file.  
* Perform at most one file‑read or file‑write operation per request.  
* Do not make outbound network connections or invoke external services.  
* The service must run under a user account that has read/write permission only to the `configs/` directory.  
* All error responses should be clear but should not disclose sensitive details.  

This ticket outlines the expected behavior and security constraints for a configuration file manager that protects against path traversal, prevents command injection during backup, enforces authorization on delete operations, and mitigates CSRF for state‑changing requests.