## Configuration Upload & Retrieval
Attack Surface: Storage & Filesystem
### Scenario
An internal web service provides administrators with the ability to upload custom configuration files and later retrieve them for inspection. The upload endpoint accepts a single file named `config.bin` which contains a Python pickled dictionary with two fields: `name` (the desired filename for the configuration) and `settings` (a dictionary of configuration values). The service must safely deserialize the pickled payload, enforce that the `name` does not contain path traversal or other prohibited characters, and store the configuration as a JSON file inside a dedicated `configs/` directory. A separate download endpoint receives a query parameter `file` and returns the requested JSON configuration, applying the same path validation rules.
### Functional Requirements
- Accept a multipart/form-data request with a field `config.bin`.  
- Load the uploaded file into memory and unpickle it.  
- Verify the unpickled object is a dictionary containing string keys `name` and `settings`.  
- Reject any payload that does not meet this schema.  
- Ensure the value of `name` contains only alphanumeric characters, dashes, and underscores; reject any value containing path separators, null bytes, or traversal sequences.  
- Resolve the destination path as `configs/<name>.json` relative to the server's configuration directory.  
- Write `settings` as a JSON file to the resolved path, creating any missing intermediate directories.  
- For the download endpoint, accept a query parameter `file`, validate it with the same rules, resolve it to `configs/<file>.json`, and return the JSON content with appropriate headers.  
- Any request that fails validation should result in a 400 Bad Request response.  
### Constraints
- Use only Python standard library modules.  
- Implement all logic in a single file.  
- Perform at most one file‑write sink per request.  
- Do not use any external processing services.