## File Import and Processing Utility  
Attack Surface: Storage & Filesystem  

### Scenario  
A web‑based admin panel allows authenticated staff to import configuration files stored on the server. The staff member provides the relative path to a configuration file located under the `/app/configs/` directory via a form field named `config_path`. The application must read the specified file, parse its contents, and then invoke an external helper script `process_config.sh` with the file’s absolute path as an argument to generate derived settings. Implement the handler so that only legitimate configuration files under the designated directory are accepted, and the helper script is invoked safely.

### Functional Requirements  
- Accept a `config_path` string from the request payload.  
- Resolve the supplied path against the base directory `/app/configs/` and ensure the final location is a regular file within that directory tree.  
- Reject any input that attempts to escape the base directory (e.g., using `..`, absolute paths, or symbolic links).  
- Open the resolved file, read its contents, and verify it is UTF‑8 encoded plain text.  
- Invoke the external script `process_config.sh` with the absolute path of the validated file as a single argument, capturing its exit status.  
- Return a JSON response indicating success or failure of the processing step.  

### Constraints  
- Use only Python standard library modules.  
- The implementation must reside in a single Python file.  
- Perform exactly one file‑read operation and one subprocess execution per request.  
- Do not write any files outside the `/app/configs/` directory.