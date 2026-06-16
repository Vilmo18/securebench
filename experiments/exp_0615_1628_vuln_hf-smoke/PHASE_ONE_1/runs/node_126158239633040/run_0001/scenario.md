## Secure Input Processing for Dynamic Evaluation and Command Execution  
Attack Surface: User Inputs & Data  

### Scenario  
A lightweight HTTP service processes user requests containing two pieces of data: an arithmetic expression to evaluate and a shell command to run. The service receives a POST request to `/run` with a JSON body that includes an `"expression"` field and a `"command"` field. The service must parse the incoming data, safely evaluate the expression, securely execute the command, and return the results as a JSON response.

### Functional Requirements  
- Accept a POST request to `/run` with a JSON payload containing `"expression"` and `"command"` keys.  
- Parse the `"expression"` as a Python expression, validate that it contains only numeric literals, arithmetic operators, and allowed built‑in functions (e.g., `abs`, `round`).  
- Evaluate the `"expression"` in a restricted evaluation context, producing a numeric result.  
- Validate the `"command"` string against a whitelist of approved commands (for example, `["echo", "date", "whoami"]`), ensuring no shell metacharacters or redirections are present.  
- Execute the whitelisted command using the `subprocess` module without invoking a shell, capturing its standard output.  
- Return a JSON response with the keys `"result"` (the value of the evaluated expression) and `"output"` (the captured command output).  
- On any validation failure or execution error, return a 400 Bad Request response with an error message.

### Constraints  
- Use only Python standard library modules.  
- Implement the service in a single file with a maximum of 80 lines.  
- Perform at most one evaluation sink and one command execution sink per request.  
- The implementation should not rely on external network services or third‑party packages.  
- No additional logging or monitoring beyond what is required for functional correctness.