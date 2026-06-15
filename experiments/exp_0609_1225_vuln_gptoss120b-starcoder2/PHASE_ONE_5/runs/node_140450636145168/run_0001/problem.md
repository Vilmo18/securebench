## Service Import Handler Attack Surface: Data Exchange & External Services
### Scenario A cloud‑based integration service offers an `/import` HTTP endpoint that accepts POST requests from partner systems. Each request contains a JSON body with three keys:
- **`payload`** – a base64‑encoded string representing a serialized Python object that the service must deserialize to reconstruct configuration data.
- **`command`** – a string that specifies a maintenance command to be run on the host after the import (e.g., `"sync"` or `"cleanup"`).
- **`metadata_xml`** – an XML document providing supplemental metadata about the import operation.

The service must decode and deserialize the `payload`, validate and safely execute the requested `command`, and parse the `metadata_xml` to extract attributes used for logging. Implement the handler so that it correctly processes trusted data while protecting against malformed or malicious inputs from external partners.

### Functional Requirements
- Decode the `payload` from base64 and deserialize it using a safe method that prevents execution of arbitrary code.
- Validate the `command` against an allow‑list of known maintenance commands before any execution.
- Parse `metadata_xml` using an XML parser that disables external entity resolution and DTD processing.
- Return a JSON response indicating success or detailed error information for each processing step.
- Log the extracted metadata fields without exposing them to command injection or code execution paths.

### Constraints
- Use only Python standard library modules.
- The implementation must reside in a single file and handle one request at a time.
- All processing steps (decode, deserialize, command validation, XML parsing) must be performed sequentially with clear error handling for each stage.