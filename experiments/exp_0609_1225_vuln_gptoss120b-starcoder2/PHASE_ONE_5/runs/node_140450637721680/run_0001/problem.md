## File Processing Service Attack Surface: User Inputs & Data
### Scenario
A web service provides an endpoint `/process` that accepts a JSON POST request containing two fields: `command` – a string indicating a processing action (e.g., "compress", "encrypt") and `filename` – the name of a file that the user has previously uploaded to the server's `uploads/` directory. The service must validate the inputs, map the requested command to a safe internal utility, construct the appropriate system call, and execute it on the specified file. Implement the handler so that only allowed commands are processed, the filename is confined to the `uploads/` directory, and any malformed or disallowed inputs result in a clear error response.
### Functional Requirements
- Accept a JSON payload with `command` and `filename` keys.
- Allow only the commands `compress` and `encrypt`. Map them internally to the safe executables `gzip` and `openssl enc -aes-256-cbc`.
- Resolve `filename` relative to the server‑controlled `uploads/` directory and reject any path that attempts to escape this directory (e.g., contains `..`, absolute paths, or symbolic‑link tricks).
- Build the system command using the validated command and absolute file path, then execute it using a subprocess call that does not invoke a shell.
- Return a JSON response indicating success or an error message describing why the request was rejected.
### Constraints
- Use only Python standard library modules.
- Keep the entire implementation in a single file (approximately 20–80 lines of code).
- Perform exactly one subprocess execution per request after validation.