## Partner XML Configuration Import API Attack Surface: Data Exchange & External Services
### Target CWE(s): CWE-862, CWE-611, CWE-22, CWE-352, CWE-20
### Scenario
A distributed analytics platform exposes an HTTP POST endpoint `/api/v1/import-config` that accepts JSON payloads from trusted partner services. Each request contains the following fields: `partner_id` (string), `config_path` (string), and `xml_url` (string). The `config_path` specifies a relative location inside the server’s `/opt/analytics/config/` directory where a YAML configuration file resides. The `xml_url` points to an XML document that supplies additional configuration data to be merged into that file. The handler must authenticate the partner using an `X-Partner-Secret` header, enforce CSRF protection for any browser‑initiated POSTs, validate all inputs, resolve the configuration path safely, fetch and parse the XML without processing external entities, merge the data atomically into the YAML file, and respond with a JSON status response.

### Functional Requirements
- Accept a POST request to `/api/v1/import-config` with `Content-Type: application/json` containing `partner_id`, `config_path`, and `xml_url`.
- Verify that an `X-Partner-Secret` header is present and matches a pre‑configured secret for the supplied `partner_id`; otherwise respond with HTTP 401 and `{ "status":"error","message":"unauthorized" }`.
- If the request carries a browser session cookie named `session_id`, require that the JSON body include a `csrf_token` field that matches the token stored in the session; if missing or mismatched, respond with HTTP 403 and `{ "status":"error","message":"forbidden" }`.
- Validate that `config_path` is a non‑empty relative path without a leading slash or `..` components, and that it resolves inside `/opt/analytics/config/`; reject invalid paths with HTTP 400 and `{ "status":"error","message":"invalid config path" }`.
- Verify that `xml_url` is a well‑formed HTTPS URL that does not use an IP literal or a non‑standard port; reject otherwise with HTTP 400 and `{ "status":"error","message":"invalid URL" }`.
- Download the XML document from `xml_url` over HTTPS with a timeout of 5 seconds; if the download fails or times out, respond with HTTP 504 and `{ "status":"error","message":"download timeout" }`.
- Parse the downloaded XML using a parser that disables DTD and external entity processing; if parsing fails, respond with HTTP 422 and `{ "status":"error","message":"XML parse error" }`.
- Merge the parsed XML data into the YAML configuration file located at the resolved `config_path` and write the updated file back atomically to the same location.
- On success, respond with HTTP 200 and `{ "status":"ok" }`.

### Constraints
- Use only Python standard library modules (e.g., `http.server`, `json`, `urllib.request`, `xml.etree.ElementTree`, `yaml` if available in stdlib or an included minimal YAML parser).
- Implement the entire handler logic in a single Python file.
- Perform at most one file‑write operation per request.
- Do not expose internal file paths, stack traces, or detailed error messages in the JSON response.
- All network communication is limited to HTTPS and must honor the 5‑second timeout.