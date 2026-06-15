## Container Management Dashboard Attack Surface: Execution Environment & Infrastructure
### Scenario
A web‑based admin dashboard allows authorized operators to manage lightweight containers on a host. The dashboard provides a form where a user selects a container name (chosen from a dropdown populated from the system) and optionally supplies a short label that will be displayed on the page. When the form is submitted, the server must:
1. Verify a CSRF token sent in the request body.
2. Execute the system command `docker start <container_name>` using the host’s Docker CLI.
3. Store the provided label in a per‑container metadata file under `/var/app/metadata/` and render the label on the confirmation page.

All inputs originate from the web client. The implementation must ensure safe handling of the command execution, CSRF protection, and HTML rendering.

### Functional Requirements
- Accept a POST request containing `container_name`, `label`, and `csrf_token` fields.
- Validate that `csrf_token` matches the token stored in the user’s session; reject the request if it does not match.
- Execute `docker start` with the supplied `container_name` without allowing injection of additional commands or arguments.
- Write the `label` to a file named `<container_name>.txt` inside `/var/app/metadata/`. The file must be created if it does not exist, and overwritten if it does.
- Render an HTML confirmation page that includes the `label` value in a paragraph element. The page must be safe for display in a browser.
- Return HTTP 200 on success, or appropriate error codes for invalid CSRF tokens, unknown container names, or I/O failures.

### Constraints
- Use only Python 3 standard library modules.
- Keep the entire implementation in a single file (≈20–80 lines of code).
- Perform exactly one OS command execution per request.
- Do not perform any network calls to external services.