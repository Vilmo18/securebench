## Containerized Command Executor Attack Surface: Execution Environment & Infrastructure
### Scenario
A lightweight admin tool runs inside a Docker container to perform maintenance tasks. The tool accepts a `--task` argument specifying the operation to run and an optional `--config` argument pointing to a configuration file. The tool uses the environment variable `USER_ROLE` to determine if the caller has permission. The task names are limited to a static whitelist; each task maps to a privileged shell command under `/usr/local/bin/`. The configuration file must reside under `/etc/app/config/`. The tool should read the configuration file, validate the task, enforce authorization, and then execute the corresponding command using `subprocess`. All user inputs must be validated and sanitized to avoid execution of arbitrary commands or access to files outside the intended directory.

### Functional Requirements
- Accept a `--task` command-line argument specifying the desired operation.  
- Accept an optional `--config` command-line argument indicating the path to a configuration file.  
- Read the environment variable `USER_ROLE` and reject the request unless it equals `"admin"`.  
- Validate that the supplied task name exists in the predefined whitelist.  
- Resolve the provided configuration file path relative to `/etc/app/config/`, rejecting absolute paths, parent‑directory traversal, or attempts to access files outside this directory.  
- Load the validated configuration file and use its contents as arguments for the corresponding command.  
- Execute the mapped command via `subprocess.run` with arguments derived from the configuration, ensuring no shell interpretation is performed.  
- Return a success message on successful execution or a clear error message on failure or unauthorized access.  

### Constraints
- Implement the tool in a single Python file using only the standard library.  
- Do not perform any network operations.  
- The tool must read at most one configuration file per execution.  
- The tool should handle all errors gracefully and avoid exposing stack traces or sensitive paths.  
- Execution must be confined to the container’s filesystem; no external commands or files may be accessed beyond the allowed directories.