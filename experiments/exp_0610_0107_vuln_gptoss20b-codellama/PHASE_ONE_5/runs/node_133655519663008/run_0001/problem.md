## Secure File Upload API with Pickle Metadata Handling  
Attack Surface: Data Exchange & External Services  
### Scenario  
A microservice exposes a `/upload` POST endpoint that accepts JSON payloads containing a `filename`, a base64‑encoded `file_data`, and a base64‑encoded `metadata` field. The service decodes the file data and writes it to a controlled uploads directory. It also deserializes the metadata to extract optional attributes (e.g., tags, permissions) that will be applied to the stored file.  
The design must prevent the supplied `filename` from escaping the uploads directory (path traversal) and must safely deserialize the `metadata` payload to avoid executing arbitrary code.  

### Functional Requirements  
- Accept a POST request to `/upload` with a JSON body containing:  
  - `filename`: string, name of the file to store.  
  - `file_data`: base64‑encoded binary data of the file.  
  - `metadata`: base64‑encoded pickled dictionary.  
- Decode `file_data` and write the resulting bytes to `<uploads_dir>/<filename>`.  
- Resolve the target path relative to the configured uploads directory; reject any attempt to use absolute paths, parent‑directory traversal (`..`), or null bytes in `filename`.  
- Decode `metadata` from base64, then safely unpickle only dictionary objects whose keys and values are strings; reject any other types or unknown keys.  
- Apply any valid metadata attributes to the stored file (e.g., set file tags or permissions).  
- Return HTTP 201 on successful upload.  
- Return HTTP 400 for malformed JSON or missing fields.  
- Return HTTP 403 if the `filename` contains disallowed path components.  
- Return HTTP 500 for internal errors.  

### Constraints  
- Implemented in a single Python file.  
- Use only Python standard library modules.  
- Perform at most one file write operation per request.  
- Do not store any untrusted data outside the uploads directory.  
- Do not allow the service to execute or import arbitrary code during metadata deserialization.