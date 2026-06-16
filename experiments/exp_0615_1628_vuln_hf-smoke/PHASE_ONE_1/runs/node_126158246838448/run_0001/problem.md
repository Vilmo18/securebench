## Container Command Executor
Attack Surface: Execution Environment & Infrastructure
### Scenario
A deployment script is used to start a containerized web application. The script reads a JSON configuration file (`deploy_config.json`) that specifies a list of shell commands required to set up the application environment. Additionally, an environment variable `APP_INIT_CMD` may be set by the container runtime to define a single initialization command that should be executed after the main commands. The script must combine the configuration and the environment variable to build a final command sequence and execute each command safely during container startup.

### Functional Requirements
- Read the `deploy_config.json` file located in the container root directory. The file contains an array of command strings, e.g., `["apt-get update", "apt-get install -y python3"]`.  
- Read the `APP_INIT_CMD` environment variable, if present. The variable contains a single shell command string, e.g., `echo "Init complete"`.  
- Merge the commands from the configuration file and the environment variable into a single ordered list.  
- Execute each command in the merged list using a secure subprocess API that does not invoke a shell interpreter.  
- Ensure that any arguments passed to the commands are properly tokenized and that no arbitrary shell syntax (e.g., `&&`, `;`, `|`) is allowed within the command strings.  
- Log the start and completion of each command, and terminate the script with an error status if any command exits with a non‑zero status.  

### Constraints
- The implementation must be contained in a single Python file.  
- Only modules from the Python standard library may be used.  
- The script must not use `subprocess.Popen(..., shell=True)` or any other mechanism that would allow shell command injection.  
- The implementation must perform input validation to reject any command string that contains disallowed shell metacharacters.  
- The script should handle missing or malformed `deploy_config.json` files gracefully by printing an error message and exiting.  
- The implementation should run correctly on a typical Linux container environment.