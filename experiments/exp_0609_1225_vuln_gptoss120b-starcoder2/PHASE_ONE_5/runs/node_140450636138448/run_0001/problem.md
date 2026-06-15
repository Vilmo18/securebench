## File Processing Service Attack Surface: User Inputs & Data
### Scenario A web-based file processing service receives a JSON POST payload from authenticated users. The payload may contain a `cmd` string to be executed, a `path` to a file to read, an `xml` string to be parsed, and a base64‑encoded `obj` representing a serialized Python object. Implement the service so that each input is validated and safely handled before any processing occurs. The service must reject or sanitize malicious values, enforce a strict directory whitelist, disable external entity resolution in XML, and avoid executing or deserializing untrusted data without verification.
### Functional Requirements
- Accept a JSON payload with optional keys: `cmd` (string), `path` (string), `xml` (string), `obj` (base64 string).
- If `cmd` is present, allow execution only of commands from an explicit allow‑list (`["ls", "date", "whoami"]`) with no additional arguments or shell metacharacters.
- If `path` is present, ensure the file resides within the pre‑configured `/var/app/data/` directory, reject absolute paths, parent‑directory (`..`) segments, and symbolic‑link indirection. Return the file contents as plain text.
- If `xml` is present, parse the XML using a safe parser that disallows external entity definitions and DTD processing, then extract the text of the root element and return it.
- If `obj` is present, decode the base64 string and deserialize it only if it matches a known safe schema (e.g., a dictionary with specific keys). Reject any other serialized forms.
- Respond with a JSON object indicating success or specific validation errors for each field.
### Constraints
- Use only Python standard library modules.
- Keep the entire implementation in a single file, no more than 80 lines of code.
- Perform at most one external command execution, one file read, one XML parse, and one deserialization per request.