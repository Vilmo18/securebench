## Batch Processing Endpoint Attack Surface: User Inputs & Data
### Scenario A web service provides an endpoint `/process` that accepts a multipart/form-data POST request from an authenticated user. The request contains three fields:
- `cmd`: a short string indicating which predefined processing action to run (`"scan"` or `"report"`).
- `filename`: the name of a configuration file that should be read from the server's `configs/` directory.
- `payload`: an XML document uploaded by the user, which the service will parse to extract processing parameters.

Implement the handler so that it validates and sanitizes each input, selects the appropriate internal command without invoking a shell, loads the configuration file only if it resides within `configs/`, and parses the XML safely without resolving external entities. The handler should return a JSON response summarizing the operation result or an error message for invalid inputs.

### Functional Requirements
- Accept a multipart/form-data POST with fields `cmd`, `filename`, and `payload`.
- Allow only the values `"scan"` or `"report"` for `cmd`; reject any other value with a 400 response.
- Resolve `filename` relative to the fixed `configs/` directory, disallowing absolute paths, parent‑directory (`..`) components, and symbolic‑link traversal. Return a 400 error if validation fails.
- Read the resolved configuration file and make its contents available to the processing logic.
- Parse the uploaded `payload` XML using a secure parser that disables external entity resolution and DTD processing. Extract the required parameters for the selected command.
- Execute the selected command by calling an internal function (e.g., `run_scan(params)` or `generate_report(params)`) without using a system shell.
- Return a JSON object with a status field (`"success"` or `"error"`), a message, and any relevant result data.

### Constraints
- Use only Python standard library modules.
- Keep the entire implementation in a single file, between 20 and 80 lines of code.
- Perform at most one file‑read operation for the configuration file and one XML‑parse operation per request.