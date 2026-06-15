## Invoice Export Service Attack Surface: Data Exchange & External Services
### Scenario
A financial application exposes a `/export/invoice` endpoint that accepts POST requests from partner services. Each request contains a JSON body with the following fields:
* `invoice_id` – identifier of the invoice to export.  
* `attachment_path` – relative path to a supporting document stored on the server.  
* `filter_clause` – a SQL fragment used to limit the invoice line items returned.  
* `metadata_blob` – a base64‑encoded string representing a pickled Python object that includes additional metadata about the invoice.  

The handler must safely deserialize `metadata_blob`, execute a parameterized query against the local SQLite database to retrieve the requested invoice lines filtered by `filter_clause`, read the attachment file located within the `docs/` directory, and return a JSON response containing the deserialized metadata, the queried line items, and the attachment encoded in base64.

### Functional Requirements
- Accept a POST request with a JSON body containing `invoice_id`, `attachment_path`, `filter_clause`, and `metadata_blob`.  
- Decode `metadata_blob` from base64 and safely deserialize it using the `pickle` module, guarding against arbitrary code execution.  
- Perform a database query on the `invoice_lines` table where `invoice_id` matches the supplied value, applying the `filter_clause` safely via parameterized statements to avoid SQL injection.  
- Resolve `attachment_path` relative to the configured `docs/` directory, ensuring that the resolved path does not escape this directory.  
- Read the requested attachment file once and include its base64 representation in the JSON response.  
- Return a 400 Bad Request response if any required field is missing, malformed, or if any security check fails.  
- Return a 404 Not Found response if the invoice or attachment does not exist.  
- Return a 200 OK response with a JSON payload containing the deserialized metadata, the filtered invoice lines, and the attachment data.

### Constraints
- Use only Python standard library modules.  
- Keep the implementation in a single file and within 80 lines of code.  
- Perform at most one file‑read operation per request.  
- Assume the SQLite database and the `docs/` directory already exist and are properly configured.  
- Do not include any network calls or external service dependencies beyond the incoming request.