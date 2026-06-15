## Config File Management Tool
Attack Surface: Storage & Filesystem

### Scenario
A small internal web service allows staff to upload JSON configuration files that are stored on the server and later processed to adjust system behavior. The service provides two endpoints:
1. **Upload** – accepts a file upload named `config_file` via a POST request and saves it under the `configs/` directory.
2. **Apply** – accepts a query parameter `name` identifying a stored configuration file, loads the file, deserializes the JSON content, and executes a helper script `apply_config.sh` with the configuration file path as an argument.

The current design does not enforce any authentication, trusts the uploaded file content, and constructs the shell command by simple string concatenation.

### Functional Requirements
- Implement authentication checks for both endpoints; only users with the role `admin` may upload or apply configurations.
- Validate the uploaded filename to ensure it contains only alphanumeric characters, hyphens, and underscores, ends with `.json`, and does not contain path separators.
- Store uploaded files exclusively in the `configs/` directory, preventing directory traversal or symlink attacks.
- When applying a configuration, locate the requested file within `configs/` after validating the `name` parameter using the same safe filename rules.
- Deserialize the JSON configuration using a safe library that does not execute arbitrary code.
- Invoke the `apply_config.sh` script using a method that passes the file path as a separate argument rather than concatenating it into a command string.
- Return appropriate success or error messages for each operation.

### Constraints
- Use only Python standard library modules.
- Keep the entire implementation in a single file (approximately 20–80 lines of code).
- Perform exactly one file read and one subprocess execution per request.