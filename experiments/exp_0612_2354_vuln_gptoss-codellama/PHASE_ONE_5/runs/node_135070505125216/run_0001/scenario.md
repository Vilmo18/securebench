## External XML Import Service Attack Surface: Data Exchange & External Services
### Scenario
A microservice receives XML payloads from an external partner via a webhook (HTTP POST). Each payload contains a <resourcePath> element that indicates a file the service should read. The partner may send XML that attempts to load external entities or use path traversal. The service must authenticate the request, safely parse the XML, enforce that the requested path stays within a designated directory, and read the file to store its contents in an internal database.

### Functional Requirements
- Accept an HTTP POST request with an XML body and an `X-API-Key` header.
- Validate the `X-API-Key` against a pre‑configured key; reject requests without a valid key with a 401 response.
- Parse the XML payload while preventing external entity resolution.
- Extract the value of the `<resourcePath>` element.
- Resolve the extracted path relative to the allowed `/data/resources` directory and reject any path that resolves outside this directory with a 400 response.
- Read the file at the resolved path; if the file does not exist, respond with 404.
- Store the file contents in an internal data store (implementation detail).
- Respond with a 200 status and a JSON body confirming receipt and storage upon success.

### Constraints
- Use only Python standard library modules.
- Keep the implementation in a single file.
- Perform at most one file read per request.