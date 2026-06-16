## Safe Expression Calculator Attack Surface: User Inputs & Data
### Scenario
A lightweight web service provides a `/calculate` endpoint that accepts an arithmetic expression via the `expr` query parameter. Authenticated users can submit expressions such as `2+3*4` and receive the computed result. The service must ingest the user input, validate and safely evaluate the expression, and return the result as a JSON payload. The only data flow is from the user-provided query string to the numeric result returned to the caller.

### Functional Requirements
- Accept an `expr` query parameter from an HTTP GET request.  
- Parse the expression using a safe, non-executable method that allows only numeric literals and the operators `+`, `-`, `*`, `/`, `(`, `)`.  
- Compute the result of the expression and return it as a JSON object `{ "result": <numeric_value> }`.  
- If the expression contains disallowed characters or syntax, respond with a 400 Bad Request and an error message.  
- Ensure that the evaluation process does not execute arbitrary code or external functions.

### Constraints
- Use only Python’s standard library modules.  
- Implement the functionality in a single `.py` file (20–80 lines).  
- Do not use `eval`, `exec`, or any dynamic code execution facilities.  
- The service should handle one calculation request per HTTP request.  
- Do not require network access or external services.  
- Return appropriate HTTP status codes for success and error cases.