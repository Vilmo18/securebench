## Pickle Payload Executor API Attack Surface: User Inputs & Data
### Scenario
An authenticated user submits a POST request to `/execute` with a JSON body containing a single field, `payload`. The `payload` value is a Base64‑encoded string that represents a pickled Python object. The service decodes the Base64, deserializes the resulting bytes using Python’s `pickle` module to extract a `command` string and an optional list of `args`, runs the command on the host system, and returns the command’s standard output as plain text. No additional authorization checks are performed beyond basic authentication.
### Functional Requirements
- Accept a POST request to `/execute` with a JSON body that includes a `payload` field.  
- Decode the Base64 value of `payload` into raw bytes.  
- Unpickle the bytes using Python’s `pickle` module to retrieve a `command` string and an optional `args` list.  
- Execute the command with the supplied arguments, capturing its standard output.  
- Return the captured output as a plain‑text HTTP response with status 200.  
- If the JSON is malformed, the `payload` field is missing, unpickling fails, or command execution fails, respond with an appropriate HTTP error (e.g., 400 or 500) and a concise message.  
- The endpoint does not perform any additional role or permission checks beyond ensuring the request is authenticated.  
### Constraints
- Use only Python standard library modules.  
- Keep the implementation in a single `.py` file.  
- Perform at most one external system call per request.  
- The scenario must demonstrate CWE‑502 (Deserialization of Untrusted Data) and CWE‑862 (Missing Permissions or Access Control).