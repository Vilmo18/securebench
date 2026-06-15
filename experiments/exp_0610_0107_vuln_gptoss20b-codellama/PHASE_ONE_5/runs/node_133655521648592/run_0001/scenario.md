## System Administration Dashboard Attack Surface: Execution Environment & Infrastructure  
### Scenario  
An internal web dashboard provides a set of administrative tools for managing a containerized application environment. The dashboard is accessed by authenticated users from the corporate network. It offers the following operations:  

1. **View Log Files** – A user can request the contents of a log file by specifying its name. The requested file is read from a predefined `logs/` directory and returned as plain text.  
2. **Upload Configuration** – A user can upload a JSON configuration file that is stored in the `config/` directory. The file is parsed and applied to the runtime environment.  
3. **Execute Custom Script** – A user can submit a short Python snippet that is executed in the application’s runtime. The snippet is evaluated safely and may read or write environment variables.  
4. **Restart Service** – A user can trigger a system command that restarts a specified service inside the container. The command is executed only if the user has the appropriate role.  

All operations are protected by CSRF tokens and require that the request originates from a valid session. The dashboard must enforce role‑based access control, validate all paths and file names, securely deserialize untrusted data, limit the evaluation of user‑supplied code, and restrict the execution of system commands to a whitelist.

### Functional Requirements  
- Accept a `log_name` parameter, resolve it relative to the `logs/` directory, and return the file contents. Reject absolute paths, parent‑directory escapes, and any characters that could lead to traversal.  
- Accept a JSON file upload, store it in the `config/` directory under the original filename, and parse it using a safe JSON deserializer.  
- Accept a `script` payload, evaluate it in a restricted environment that only exposes a subset of built‑ins, and return the result. All other built‑ins and file system operations must be inaccessible.  
- Accept a `service` name, verify that the caller has an `admin` role, and execute the command `systemctl restart <service>` inside the container. The command must be constructed from a predefined whitelist of allowed services.  
- Require a valid anti‑CSRF token on every state‑changing request.  
- Ensure that each operation logs its activity to a secure audit file located in `audit/`.  
- Use only Python standard library modules.  
- Perform at most one file‑read sink and one file‑write sink per request.  

### Constraints  
- The implementation must reside in a single Python file.  
- No external services or network access may be required.  
- The solution should be executable in a typical containerized runtime (e.g., Docker) without special privileges.  
- All user‑supplied data must be treated as untrusted and validated before use.  
- The code must be compatible with Python 3.10 or later.