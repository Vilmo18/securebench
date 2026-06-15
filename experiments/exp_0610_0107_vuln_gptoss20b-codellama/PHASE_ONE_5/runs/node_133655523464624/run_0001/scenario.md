## Config Upload Handler
Attack Surface: User Inputs & Data
### Scenario
A corporate intranet application allows administrators to upload custom configuration profiles via a web form. The form posts a JSON payload containing a field `config_blob` that holds a base64‑encoded, serialized Python dictionary with configuration settings. The application must deserialize the payload, validate its contents, and apply the settings to the running service. The user input is the `config_blob` field, which is untrusted.

### Functional Requirements
- Accept a POST request to `/admin/upload-config` with a JSON body containing a single key `config_blob`.  
- Verify that the request body is valid JSON and that the key `config_blob` is present.  
- Decode the base64 value to bytes; reject the request if decoding fails or the decoded data exceeds 64 KiB.  
- Load the decoded bytes using `pickle.loads`; any exception during loading must result in a 400 response.  
- Confirm that the deserialized object is a dictionary.  
- Ensure the dictionary contains only the allowed keys: `timeout`, `max_connections`, `enable_logging`.  
- For each key, verify that the value is an integer within a safe range (`timeout`: 1–300, `max_connections`: 1–1000, `enable_logging`: 0 or 1).  
- Apply the validated settings to the application's in‑memory configuration module.  
- Return a 200 OK response with JSON `{ "status": "success" }` upon successful update; otherwise return 400 with a descriptive error message.

### Constraints
- Use only Python 3 standard library modules.  
- Implement the handler in a single Python file.  
- Perform at most one pickle load per request.  
- Do not write the configuration to disk; only update in‑memory settings.