## Custom Email Template Rendering Endpoint Attack Surface: Web Outputs & Rendering
### Scenario
A web service offers an endpoint `/render_template` that accepts a JSON payload with two fields: `template` and `data`. The `template` field contains a string that may embed expressions to be evaluated against the `data` dictionary, producing an HTML email body. The endpoint is currently accessible to all authenticated users and internally performs the rendering by passing the template string to Python's `eval`. The new implementation must restrict access so that only users with the role `admin` can use this endpoint, and it must replace the unsafe `eval`-based rendering with a safe templating approach that only supports simple variable interpolation. The rendered HTML should be returned to the client as a plain text response with the `Content-Type: text/html` header.

### Functional Requirements
- Accept a POST request to `/render_template` with a JSON body containing:
  - `template`: a string with placeholders for variables.
  - `data`: a dictionary mapping variable names to string values.
- Verify that the requester has the `admin` role before proceeding; otherwise, return a 403 Forbidden response.
- Render the `template` safely by substituting placeholders with values from `data` without executing arbitrary code.
- Return the resulting HTML string in the response body with the `Content-Type: text/html` header.
- If the `template` contains unsupported syntax or references to missing variables, return a 400 Bad Request with a clear error message.
- Log the request details and the outcome for audit purposes.

### Constraints
- Use only Python standard library modules.
- Keep the implementation in a single file.
- Perform at most one output sink per request.