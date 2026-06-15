## Secure Payload Processor Attack Surface: User Inputs & Data

### Scenario
A web API hosts an endpoint `/process` that accepts a JSON payload from a client. The JSON body contains a single field `payload`, which is a base64‑encoded representation of a Python serialized object. The service must decode the base64 string, safely deserialize the object, extract the `command` attribute, and perform a logged operation based on that command. The application is expected to run behind a local network and has no external service dependencies.

### Functional Requirements
- Accept an HTTP POST request to `/process` with `Content-Type: application/json`.  
- The request body must contain a JSON object with a required key `payload` holding a base64‑encoded string.  
- Decode the base64 string; if decoding fails, respond with HTTP 400.  
- Deserialize the decoded bytes using a restricted unpickler that only permits built‑in types (`int`, `str`, `list`, `dict`) and a single custom class `Command`.  
- The `Command` class has a mandatory attribute `command` of type `str`.  
- After successful deserialization, extract the `command` attribute and return a JSON response: `{"status":"ok","command":<extracted_value>}` with HTTP 200.  
- If deserialization fails, the payload is not of the allowed type, or the required attribute is missing, respond with HTTP 400.  
- Log the request method, endpoint, and the extracted command value for audit purposes.

### Constraints
- Use only Python standard library modules.  
- The implementation must fit within a single Python file and be no longer than 80 lines.  
- Perform at most one deserialization operation per request.  
- Do not write the deserialized object to disk or invoke any external services.  
- The endpoint should be stateless and not rely on session or cookie data.