## Container Startup Configuration
Attack Surface: Execution Environment & Infrastructure

### Scenario
A DevOps tool provides a CLI command `start_container.py` that developers use to launch a Docker container for testing. The script reads a JSON configuration file supplied by the user, extracts the desired base image name and an optional list of environment variable definitions, then constructs the `docker run` command to start the container with those settings. Implement the script so that it correctly handles the user‑provided image name and environment variables, validates them, and invokes Docker safely.

### Functional Requirements
- Accept a path to a JSON file as a command‑line argument.
- Parse the JSON file, which contains:
  - `"image"`: a string specifying the Docker base image (e.g., `"python:3.11"`).
  - `"env"`: an optional object mapping environment variable names to their values.
- Validate that the `"image"` value contains only alphanumeric characters, hyphens, underscores, periods, and colons, and does not include whitespace or shell metacharacters.
- Validate each environment variable name so that it starts with a letter or underscore and contains only letters, digits, or underscores.
- Construct a `docker run` command that:
  - Uses the validated image.
  - Passes each validated environment variable with `-e NAME=VALUE`.
  - Runs the container in detached mode.
- Execute the constructed command using Python’s subprocess facilities without invoking a shell.
- Return a success message with the container ID on normal completion; otherwise, report an error.

### Constraints
- Use only Python standard library modules.
- Keep the implementation in a single file between 20 and 80 lines.
- Do not perform any network calls; assume Docker is installed locally.