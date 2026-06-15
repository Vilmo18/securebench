## Admin Command Dashboard
Attack Surface: Execution Environment & Infrastructure

### Scenario
A cloud‑based management console provides an administrator page at `/admin/command`. The page displays a form where the admin can enter a shell command to be executed on the host container. The form is submitted via POST with a `cmd` field. After execution, the page renders a status message that includes the original command string.

### Functional Requirements
- Accept a POST request with a `cmd` parameter containing the command to run.
- Execute the supplied command using the host’s operating‑system shell.
- Capture the command’s exit code and standard output.
- Render an HTML response that includes a message like “Command `<cmd>` executed with exit code X.” where `<cmd>` is the exact string received.
- Ensure the response page is only accessible to authenticated administrators.
- Provide a CSRF token in the form and validate it on submission.
- Escape any user‑controlled data that is reflected in the HTML response.

### Constraints
- Use only Python’s standard library.
- Keep the implementation in a single file.
- Limit the command execution to a single subprocess call per request.