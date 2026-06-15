## XML Configuration Importer Attack Surface: Storage & Filesystem
### Scenario
A web‑based management console allows privileged users to import a device configuration packaged as an XML file. The uploaded file is stored in a server‑controlled `configs/` directory. After saving, the application parses the XML, extracts a `<script>` element that specifies a command to be executed on the host for applying the configuration, and then runs that command using the system shell. Implement the import handler so that it correctly validates the uploaded file name, safely parses the XML without processing external entities, and executes only allowed commands derived from the XML content. The handler must also ensure that the file is written only inside the `configs/` directory and that any path manipulation attempts are rejected.

### Functional Requirements
- Accept a file upload named `config_file` via a POST request.
- Validate the uploaded filename: reject absolute paths, parent‑directory references (`..`), null bytes, and any characters outside the allowed set `[a‑zA‑Z0-9._-]`.
- Save the file under the server‑controlled `configs/` directory, creating the directory if it does not exist.
- Parse the saved XML using a secure parser that disables external entity resolution.
- Extract the text of the `<script>` element. The text must match one of the whitelisted commands: `apply`, `reset`, or `status`.
- Execute the whitelisted command with the `subprocess.run` API, passing the command name as a single argument (no shell invocation) and capture its output.
- Return a JSON response containing the command’s stdout and a success flag. If any validation step fails, return a JSON error with an appropriate message and a non‑200 HTTP status.

### Constraints
- Use only Python standard library modules.
- Keep the entire implementation within a single Python file (approximately 20–80 lines of code).
- Perform exactly one file‑write operation and one command‑execution operation per request.