## Admin Command Executor Attack Surface: User Inputs & Data
### Scenario
An internal administrative web interface provides a `/admin/execute` endpoint that allows staff with proper session cookies to run predefined system maintenance commands. The endpoint accepts a POST request containing a `command` field and a `csrf_token`. The system must validate that the command is one of a small whitelist (e.g., `restart_service`, `backup_db`, `clear_cache`) and that the CSRF token matches the one stored in the user’s session. The endpoint then executes the corresponding system command using the operating system shell and returns the standard output to the client.
### Functional Requirements
- Accept a POST request to `/admin/execute` with form data fields `command` and `csrf_token`.
- Verify that the request includes a valid session cookie identifying an authenticated administrator.
- Validate that the submitted `command` value matches one of the approved command identifiers.
- Confirm that the supplied `csrf_token` matches the token stored on the server for the current session.
- Execute the corresponding system command via the operating system shell (e.g., using `subprocess.run`) and capture its standard output and error streams.
- Return a JSON response containing the exit status, stdout, and stderr from the executed command.
- On any validation failure or execution error, return an HTTP 400 Bad Request or 403 Forbidden response with an appropriate error message.
### Constraints
- Use only Python standard library modules.
- Keep the implementation in a single Python file.
- The command execution must not allow arbitrary shell input; only whitelisted command identifiers should be permitted.
- CSRF protection must be enforced by checking the token against the session value.