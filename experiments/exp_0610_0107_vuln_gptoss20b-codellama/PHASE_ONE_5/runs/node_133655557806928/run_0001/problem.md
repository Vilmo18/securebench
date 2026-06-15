## Safe Command Executor Attack Surface: Execution Environment & Infrastructure
### Scenario
An infrastructure automation tool needs to run a system maintenance script. The tool reads the path of a configuration file from an environment variable `MAINT_CONFIG_PATH`. The configuration file contains a single line with the command to execute. The tool must load this configuration, validate the file path, ensure the command is one of a whitelist of allowed commands, and then execute it using `subprocess.run`. The configuration file path must be confined to a designated `/etc/maint/` directory. The tool should reject absolute paths, parent‑directory traversal, or paths outside the allowed directory. Only commands in the whitelist (`["apt-get update", "systemctl restart nginx"]`) are permitted. If validation fails, the tool should exit with an error message.
### Functional Requirements
- Read the `MAINT_CONFIG_PATH` environment variable.  
- Verify that the path is a relative path that resolves inside the `/etc/maint/` directory.  
- Reject paths containing `..`, absolute paths, or any form of path traversal.  
- Open and read the configuration file; the file must contain exactly one line.  
- Validate that the command line is one of the allowed whitelist commands.  
- Execute the validated command using `subprocess.run` with `shell=False`.  
- Log the command execution and exit gracefully on success.  
- Print a clear error message and exit with non‑zero status on any validation failure or execution error.  
### Constraints
- Use only Python standard library modules.  
- Implement the tool as a single Python file.  
- Do not perform more than one file read per execution.  
- The tool must not spawn arbitrary shell commands; it should use the whitelist approach and avoid `shell=True`.