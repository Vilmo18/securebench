## XML/Code/Deserialization Processor
Attack Surface: User Inputs & Data

### Scenario
A web‑based configuration service allows administrators to upload a JSON file that describes system settings. The uploaded file is sent as a multipart/form‑data POST request with the field name `config`. The service must parse the file, extract an optional embedded XML snippet (used for legacy settings), and then dynamically generate a small Python function from a user‑provided expression to compute derived values. Finally, the parsed configuration object is stored in a session cache using Python’s `pickle` module for later retrieval.

Implement the processing pipeline so that:
1. The uploaded JSON is validated against a strict schema before any further handling.
2. Any embedded XML snippet is parsed safely, disallowing external entity resolution.
3. The user‑provided expression used for the derived‑value function is compiled only if it contains allowed identifiers and operators.
4. The configuration object is serialized to a byte stream with `pickle` only after confirming that it contains only primitive data types (strings, numbers, booleans, lists, dicts) and no executable objects.

### Functional Requirements
- Accept a multipart/form‑data POST request containing a `config` file upload.
- Validate the JSON payload against a predefined schema (required fields: `name` (string), `version` (string), optional `legacy_xml` (string), optional `calc_expr` (string)).
- Parse `legacy_xml` using a secure XML parser that disables external entity resolution.
- If `calc_expr` is present, compile it into a Python function that takes a single numeric argument and returns the evaluated result, but only allow arithmetic operators and the `math` module’s safe functions.
- After successful validation and processing, serialize the resulting configuration dictionary with `pickle` and store it in an in‑memory cache keyed by the administrator’s session ID.
- Return a JSON response indicating success or detailed validation errors.

### Constraints
- Use only Python standard library modules.
- Keep the entire implementation within a single file (≈20–80 lines of code).
- Perform at most one `pickle` serialization per request.
- No network calls or external services may be used.