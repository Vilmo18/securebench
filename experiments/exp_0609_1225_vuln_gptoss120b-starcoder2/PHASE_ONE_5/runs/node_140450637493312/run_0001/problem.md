## Container Startup Configurator
Attack Surface: Execution Environment & Infrastructure

### Scenario
A DevOps utility launches a Docker container based on a user‑provided configuration file. The file path is supplied via the `CONFIG_PATH` environment variable. The utility must read the JSON configuration, extract the image name and optional command arguments, and then invoke `docker run` with those parameters. Implement the utility so it safely resolves the configuration file location, validates its contents, and constructs the command without exposing the host system to path traversal or unsafe deserialization.

### Functional Requirements
- Read the `CONFIG_PATH` environment variable to obtain the configuration file location.
- Resolve the supplied path strictly within the predefined `/etc/container_configs/` directory; reject absolute paths, parent‑directory (`..`) components, and symbolic‑link escapes.
- Open and parse the configuration file as JSON. The JSON must contain:
  - `"image"`: a non‑empty string specifying a Docker image name.
  - `"cmd"` (optional): an array of strings representing command‑line arguments to pass to the container.
- Validate that the `"image"` value matches the pattern `^[a-z0-9]+(/[a-z0-9]+)*(:[a-z0-9._-]+)?$` (lower‑case alphanumerics, optional repository path, optional tag).
- If the `"cmd"` array is present, ensure each element is a plain string without shell metacharacters.
- Construct the `docker run` command using a list of arguments (no shell string concatenation) and execute it via `subprocess.run` with `check=True`.
- Return a clear success message on successful container launch; otherwise, raise an exception with an appropriate error description.

### Constraints
- Use only Python standard library modules.
- Keep the implementation in a single file (≈20–80 lines).
- Perform exactly one file‑read operation and one subprocess execution per invocation.