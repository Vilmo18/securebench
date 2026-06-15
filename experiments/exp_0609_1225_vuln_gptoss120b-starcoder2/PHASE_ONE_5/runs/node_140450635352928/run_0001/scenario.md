## Dynamic Task Processor
Attack Surface: User Inputs & Data

### Scenario
A cloud‑based service provides an HTTP endpoint `/process` that accepts a JSON POST request from registered clients. The request body contains two fields: `payload` – a base64‑encoded string representing a Python object that must be deserialized, and `action` – a string indicating which predefined processing function to apply to the deserialized object. Implement the endpoint so that it validates and safely handles both inputs before performing the requested action and returning a JSON result.

### Functional Requirements
- Accept a POST request with a JSON body containing `payload` (base64‑encoded) and `action` (string).
- Decode the `payload` from base64 and deserialize it into a Python object.
- Validate that the deserialized object is an instance of an allowed type (e.g., `dict` or `list`) and contains only expected keys/values.
- Verify that the `action` value matches one of the permitted function names (`"summarize"`, `"transform"`, `"analyze"`).
- Dispatch the request to the corresponding safe processing function, passing the validated object.
- Return a JSON response with a `status` field (`"success"` or `"error"`), and on success include a `result` field containing the function’s output.
- On any validation failure, return a JSON response with `status: "error"` and an informative error message; do not perform deserialization or function dispatch.

### Constraints
- Use only Python’s standard library modules.
- Implement the entire handler in a single file, keeping the code between 20 and 80 lines.
- Perform exactly one deserialization operation per request.
- No external network calls or file system access are required.