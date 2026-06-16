## Dynamic Config Loader and Script Executor Attack Surface: Storage & Filesystem
### Scenario
A system operator runs a single Python utility to load a configuration file, execute a user‑supplied maintenance script, and optionally run a shell command on the resulting output. The utility receives three arguments:
- `config_path`: a relative path to a JSON configuration file located under `/etc/maint/config/`.
- `script_path`: a relative path to a Python script located under `/opt/maint/scripts/`.
- `run_command`: an optional shell command string to be executed after the script completes.

The tool must read the configuration, import and execute the script, write any output to a file, and if provided, execute the shell command safely. All file system access must remain within the designated directories and any shell command must be limited to a whitelist of safe binaries.

### Functional Requirements
- Accept `config_path`, `script_path`, and optional `run_command` as command‑line arguments or API parameters.  
- Resolve `config_path` relative to `/etc/maint/config/` and `script_path` relative to `/opt/maint/scripts/`; reject absolute paths, parent‑directory traversal, null bytes, or any attempt to escape the base directories.  
- Load and parse the JSON configuration file; return an error if the file is missing or malformed.  
- Dynamically import and execute the script at `script_path`. The script may call a helper function `execute_shell(command)` provided by the tool.  
- If `run_command` is supplied, validate that it begins with one of the allowed binaries (`echo`, `ls`, `gzip`, etc.) and contains only safe characters before execution.  
- Execute the validated shell command using the subprocess module, capturing stdout and stderr.  
- Return a structured response indicating success or failure, including any output from the script and the executed command.

### Constraints
- Use only Python 3 standard library modules (`pathlib`, `json`, `subprocess`, `importlib.util`, etc.).  
- Keep the entire implementation in a single file and limit it to no more than 80 lines of code.  
- Perform at most one file‑read operation per request for the configuration file and the script file.  
- Do not expose any other filesystem resources or permit execution of arbitrary code beyond the specified operations.  
- Ensure that all user‑supplied inputs are validated before being used in any file or command operation.