## Container Management CLI Attack Surface: Execution Environment & Infrastructure
### Scenario
A cloud operations tool provides a command‑line interface (`manage.py`) that allows internal engineers to perform container lifecycle actions. The tool reads an XML configuration file (`containers.xml`) that lists permitted container images and resource limits. It also reads a JSON blob from the environment variable `CONTAINER_PAYLOAD` which contains runtime parameters supplied by an automated CI pipeline. Based on the requested action (`start`, `stop`, or `restart`) and the target container name passed as a command‑line argument, the script builds an operating‑system command to invoke the container runtime (`docker`).

The implementation must ensure that:
- Only authorized engineers can invoke the CLI (no explicit role check is currently performed).
- The XML configuration is parsed safely, preventing external entity processing.
- The JSON payload from the environment variable is deserialized only after validation.
- The constructed OS command cannot be injected with malicious content.

### Functional Requirements
- Parse `containers.xml` to obtain a whitelist of allowed container image names.
- Load the `CONTAINER_PAYLOAD` environment variable, deserialize the JSON, and extract the fields `image`, `cpu_limit`, and `memory_limit`.
- Accept a single positional argument `action` (`start`, `stop`, or `restart`) and a required argument `container_name`.
- Verify that the requested `image` is present in the whitelist from the XML file before proceeding.
- Construct a `docker` command that includes the validated parameters and execute it using a subprocess call.
- Return a clear success message on successful execution or an error message if any validation fails.

### Constraints
- Use only Python standard library modules.
- Keep the entire implementation in a single file (approximately 20–80 lines of code).
- Perform exactly one subprocess execution per invocation.
- Do not rely on external network services or databases.