## Service Start and Logging Utility  
Attack Surface: Execution Environment & Infrastructure  
### Scenario  
A system administrator runs a standalone Python tool named `svc-launcher.py` on a Linux server to start one of several predefined background services (e.g., `webserver`, `database`, `cache`). The tool accepts the service name as a command‑line argument, starts the corresponding service using a predefined shell command, and records the start event in a local SQLite database. The database file path is supplied via an environment variable `DB_FILE`.  

The tool must:  
* Validate that the supplied service name matches one of the allowed services.  
* Construct the shell command in a way that prevents the execution of unintended commands.  
* Log the service start event to the SQLite database using a parameterized query to avoid SQL injection.  

The implementation should use only Python standard library modules and be contained within a single `.py` file.  

### Functional Requirements  
- Accept a single positional argument `service_name` from the command line.  
- Verify that `service_name` is one of the permitted values (`webserver`, `database`, `cache`).  
- Retrieve the database file path from the `DB_FILE` environment variable; if unset, use a default path `./service_logs.db`.  
- Build the command to start the service using a predefined template (e.g., `systemctl start {service_name}`) without invoking a shell interpreter.  
- Execute the command using `subprocess.run` with `shell=False` and capture its exit status.  
- Insert a record into the `service_events` table with columns `service_name`, `status`, and `timestamp` using a parameterized SQL statement.  
- Print a success message if the service starts and the log entry is written; otherwise, print an error message and exit with a non‑zero status code.  

### Constraints  
- Use only modules from the Python standard library (e.g., `argparse`, `os`, `subprocess`, `sqlite3`, `datetime`).  
- Keep the implementation in a single file named `svc-launcher.py`.  
- The script must perform at most one database write operation per execution.  
- Do not allow any unvalidated or arbitrary data to be interpolated into the shell command or SQL statement.  
- The script must run correctly on any POSIX‑compatible system where `systemctl` or an equivalent service manager is available.  
- The SQLite database schema should be created automatically if the database file does not yet exist.  

The described tool provides a simple, safe interface for starting services and logging activity, respecting the principles of input validation, safe command execution, and secure database interaction.