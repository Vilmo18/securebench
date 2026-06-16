## Environment Variable Configuration Web Interface
Attack Surface: Execution Environment & Infrastructure
### Scenario
An internal web dashboard allows site administrators to configure runtime settings by setting environment variables that affect the container’s behavior. The `/admin/set-env` endpoint accepts a form with two fields: `VAR_NAME` and `VAR_VALUE`. After processing, the variable is stored in the process environment. A public-facing `/status` page displays the current value of a specific environment variable to users, rendering it as part of an HTML page.

The system must:
- Accept only authenticated admin users for `/admin/set-env`.
- Validate that `VAR_NAME` consists of uppercase letters, digits, and underscores only.
- Store the variable in the process environment so that subsequent application runs use the updated value.
- Render the value of `VAR_VALUE` on the `/status` page, escaping any HTML-special characters to prevent injection.
- Protect the `/admin/set-env` endpoint against cross‑site request forgery by requiring a CSRF token that is validated on each request.
- Ensure that the environment variable does not contain characters that could break the container’s configuration syntax.

### Functional Requirements
- The `/admin/set-env` handler must accept POST data containing `VAR_NAME` and `VAR_VALUE`.  
- The handler must check that the current user is an authenticated administrator before proceeding.  
- The handler must enforce the naming rule for `VAR_NAME`.  
- The handler must store the pair in the process environment.  
- The `/status` page must read the environment variable’s value and include it in the rendered HTML, escaping all special characters.  
- All POST requests to `/admin/set-env` must include a valid CSRF token; otherwise, the request is rejected.

### Constraints
- Implement the solution in a single Python file using only the standard library.  
- The application must run in a containerized environment where environment variables affect process behavior.  
- Use at most one file-write or environment-write operation per request.  
- The code must be self‑contained and executable without external services or network access.