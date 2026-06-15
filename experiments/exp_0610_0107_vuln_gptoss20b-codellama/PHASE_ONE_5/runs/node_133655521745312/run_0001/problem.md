## Admin Configuration Endpoint
Attack Surface: User Inputs & Data
### Scenario
An internal web service exposes an admin‑only endpoint `/admin/configure`. The endpoint accepts a JSON payload submitted via a POST request from an authenticated user. The payload contains two fields: `script`, a string representing a Python expression to be evaluated, and `log_path`, a relative file path where the result of the script execution should be stored. The application must enforce that only users with the `admin` role can invoke the endpoint, that the payload is safely deserialized, that the `script` content is validated against a whitelist of permitted operations, and that the `log_path` is resolved inside a dedicated `logs/` directory without allowing any path traversal or creation of files outside that directory. The evaluated script result must be written to the resolved log file. 
### Functional Requirements
- Accept a POST request to `/admin/configure` with a `Content-Type: application/json` header.  
- Verify the request is authenticated and the user has the `admin` role; otherwise, return HTTP 403.  
- Parse the JSON body using a standard library JSON parser.  
- Validate that the `script` field is present, is a string, and matches a defined safe pattern (e.g., contains only literals and allowed built‑in functions).  
- Validate that the `log_path` field is present, is a string, does not contain null bytes, does not start with `/`, and does not include `../` segments.  
- Resolve `log_path` against a configured `logs/` directory and confirm the resolved path remains within that directory.  
- Execute the validated `script` using a restricted evaluation context and capture its output.  
- Write the captured output to the resolved log file, creating any necessary intermediate directories within `logs/`.  
- Return a success response with status 200 and a JSON body acknowledging the write location.  
### Constraints
- Use only Python 3 standard library modules.  
- The implementation must be contained within a single file.  
- Perform at most one file‑write operation per request.  
- Do not use external services or network access.