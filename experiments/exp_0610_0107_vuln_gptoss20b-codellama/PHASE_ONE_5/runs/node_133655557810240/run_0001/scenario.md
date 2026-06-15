## Backup Scheduler Tool Attack Surface: Execution Environment & Infrastructure
### Scenario
A system administrator runs a Python script that schedules a database backup by invoking the `mysqldump` utility inside a Docker container. The backup directory is supplied via an environment variable `BACKUP_DIR`. The script must construct a shell command that writes the dump to the specified directory within the container, respecting the host's filesystem boundaries and without allowing arbitrary command execution.
### Functional Requirements
- Read the `BACKUP_DIR` environment variable and validate it as a relative, non-absolute path that does not contain parent‑directory traversal sequences.
- Compose a Docker `exec` command that runs `mysqldump` with the validated backup directory as an argument.
- Execute the command using the `subprocess` module, capturing standard output and error streams.
- Log the backup result and exit with a success status if the dump completes without errors; otherwise, log the failure and exit with an error status.
- Reject any `BACKUP_DIR` values that fail validation, printing a clear error message and terminating the script.
### Constraints
- Use only the Python standard library.
- Keep the implementation in a single file of 20–80 lines.
- Perform no network or external service calls; the Docker container is assumed to be pre‑running locally. 
- Ensure that the script contains exactly one command‑execution sink per invocation. 
- The script must be compatible with Python 3.8 or later.