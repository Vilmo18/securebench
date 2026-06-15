## Secure Log Reader Script Attack Surface: Execution Environment & Infrastructure
### Scenario
A maintenance script runs inside a containerized environment to allow administrators to read log files located under the protected directory `/var/log/app`. The script is executed with a single positional argument specifying the log file name. Execution is permitted only for processes that have the environment variable `ROLE=admin`. The script must resolve the requested file to an absolute path, verify that it resides within `/var/log/app`, and then output its contents by invoking the `cat` command. Any attempt to read a file outside the allowed directory or to run the script without the required environment variable should result in termination with an appropriate error message.

### Functional Requirements
- Verify that the environment variable `ROLE` equals `admin`; if not, exit with code 1 and print "Unauthorized".
- Accept a single command‑line argument `log_file` indicating which log file to display.
- Resolve `log_file` to an absolute, real path relative to `/var/log/app`.
- Reject absolute paths, parent‑directory traversal, or any path that resolves outside `/var/log/app`; exit with code 2 and print "Invalid log path".
- Execute a single system call to `cat <resolved_path>` and stream its output to stdout.
- On success, exit with code 0 after displaying the file contents.

### Constraints
- Use only Python standard library modules.
- Keep the implementation in one file, approximately 20–80 lines of code.
- Perform at most one system‑call sink per execution.