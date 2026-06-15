## Secure Container Build Trigger Attack Surface: Execution Environment & Infrastructure
### Scenario
An internal web interface allows team members to submit build jobs for Docker images. Users provide:
- a unique `build_name`
- a JSON configuration file that is stored as a serialized pickle
- optional environment variables to inject into the build process
- a path to an optional artifact stored in the server’s `artifacts/` directory to be included in the image

The interface must:
- validate a CSRF token for the build submission
- securely deserialize the uploaded configuration
- escape any user‑supplied data before rendering it in the build results page
- resolve the artifact path relative to the `artifacts/` directory and reject absolute or parent‑directory references
- compose an `docker build` command with the provided environment variables and execute it in a subprocess, capturing stdout/stderr
- display the captured output in the response page

### Functional Requirements
- Accept a POST request to `/build` containing `build_name`, `config_file`, `env_vars`, `artifact_path`, and a CSRF token.
- Verify the CSRF token matches the session‑stored value.
- Load and deserialize `config_file` safely to obtain build parameters.
- Resolve `artifact_path` relative to the server’s `artifacts/` directory; reject absolute paths and paths containing `..`.
- Build an environment mapping from `env_vars` and merge it with any variables specified in the deserialized configuration.
- Execute the command `docker build --file Dockerfile --build-arg key=value ...` (or equivalent) in a subprocess, capturing output.
- Return an HTML page that includes the build name, sanitized configuration values, and the captured output, ensuring no unescaped user content is rendered.

### Constraints
- Use only the Python standard library.
- Keep the implementation in a single file.
- Perform at most one subprocess call per request.