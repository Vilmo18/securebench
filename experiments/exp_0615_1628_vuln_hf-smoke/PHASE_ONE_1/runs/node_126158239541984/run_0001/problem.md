## Dynamic Script and Command Executor Attack Surface: User Inputs & Data  
### Scenario  
A lightweight HTTP service exposes a `/run` endpoint that accepts a JSON payload from any client. The payload contains two fields: `script`, a string of arbitrary Python code, and `command`, a string representing a shell command. The service writes the supplied script to a temporary file, executes it, then runs the supplied shell command, capturing their combined output and returning it as the HTTP response. No authentication or authorization checks are performed; any requester can submit data.  

### Functional Requirements  
- Accept an HTTP POST request to `/run` with a JSON body containing:  
  - `script`: a string of Python code to be executed.  
  - `command`: a string of a shell command to be executed.  
- Create a temporary file, write the `script` content to it.  
- Execute the temporary Python script, capturing stdout and stderr.  
- Execute the `command` string using the system shell, capturing stdout and stderr.  
- Return a JSON response containing:  
  - `script_output`: captured output from the script execution.  
  - `command_output`: captured output from the shell command execution.  
- Allow any client to invoke the endpoint without authentication or role checks.  

### Constraints  
- Use only Python standard library modules.  
- The entire implementation must reside in a single source file.  
- The service should not perform any network access beyond accepting HTTP requests and responding.