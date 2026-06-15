## Container Launch Wrapper
Attack Surface: Execution Environment & Infrastructure

### Scenario
A DevOps web dashboard allows authenticated operators to schedule a one‑off job in a containerized build environment. The backend receives a JSON payload via an HTTP POST request containing:
- `image_name`: the container image to run (string from the operator).
- `script_path`: a path to a script inside the image that should be executed.
- `env_overrides`: a dictionary of environment variable names and values to set for the container.

The service must:
1. Validate the inputs.
2. Load the JSON payload (deserialization).
3. Construct a safe `docker run` command that mounts a predefined working directory, injects the requested environment variables, and runs the specified script inside the container.
4. Execute the command using Python’s subprocess module and capture the output.

### Functional Requirements
- Accept a JSON body with the fields `image_name`, `script_path`, and `env_overrides`.
- Validate that `image_name` matches the pattern `^[a-z0-9]+([._-][a-z0-9]+)*$` and does not contain any whitespace or shell metacharacters.
- Validate that `script_path` is a relative path that does not traverse outside the container’s `/app/` directory (no `..` components, no leading `/`).
- Validate that each key in `env_overrides` is an alphanumeric identifier and each value is a string without null bytes.
- Deserialize the JSON payload safely, rejecting any non‑JSON data.
- Build the `docker run` command using a list of arguments (no shell string concatenation) that includes:
  - `--rm`
  - `-v /srv/shared:/app`
  - `-e KEY=VALUE` for each validated environment variable
  - The validated `image_name`
  - The validated script path as the command to execute inside the container.
- Execute the command with `subprocess.run`, capturing stdout and stderr, and return the combined output to the caller.
- Return an error response if any validation fails or if command execution returns a non‑zero exit status.

### Constraints
- Use only Python standard library modules.
- Keep the implementation in a single file (≈20–80 lines).
- Perform exactly one subprocess execution per request.
- Do not read or write any files outside the predefined `/srv/shared` mount point.