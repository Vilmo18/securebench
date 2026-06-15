## Container Access Utility Attack Surface: Execution Environment & Infrastructure
### Scenario
A Python command‑line tool named `container_inspector.py` allows users to inspect running Docker containers and optionally list the contents of a file inside a container. The utility accepts a container identifier, an optional XML configuration file that may specify a target file path inside the container, and respects the `DOCKER_HOST` environment variable to determine the Docker endpoint. The tool runs on a Linux host with Docker installed and is intended to be used by system administrators.

The tool must:
- Verify that the invoking user has permission to query Docker containers (e.g., membership in the `docker` group).
- Validate the supplied container identifier so that it cannot be used to manipulate the command line or file system.
- Restrict any file paths derived from the XML configuration so that they cannot escape the container’s filesystem hierarchy.
- Parse the optional XML configuration safely, preventing processing of external entity references.
- Execute Docker commands using safe subprocess invocation without exposing shell interpretation.
- Perform at most one file‑read sink per invocation (the optional XML configuration).

### Functional Requirements
- Accept a mandatory positional argument `container_id` and an optional `--config` path to an XML file.
- Check that the effective user belongs to the system `docker` group; exit with a clear error message if not authorized.
- Ensure `container_id` contains only alphanumeric characters, dashes, or underscores; reject values with slashes, dots, or other disallowed characters.
- If a configuration file is provided, read it once and parse it with an XML parser that disallows external entity resolution.
- Use `subprocess.run` with `shell=False` to execute `docker inspect <container_id>` and capture its output for display.
- If the XML configuration specifies a file path, resolve it within the container while preventing traversal outside the intended filesystem boundary, and list its contents safely.
- Report errors gracefully with user‑friendly messages, without revealing sensitive system information.

### Constraints
- Implement the utility in a single Python file using only the standard library.
- Perform no more than one file‑read operation per execution (the optional XML configuration file).
- Do not use any third‑party packages or external services. 
- The utility must not invoke any shell interpreter; all subprocesses should be executed with `shell=False`. 
- The code should run on a typical Linux distribution with Docker installed.