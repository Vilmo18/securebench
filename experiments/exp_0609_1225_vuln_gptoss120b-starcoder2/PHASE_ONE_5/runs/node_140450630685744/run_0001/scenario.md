## Configurable Report Generator  
Attack Surface: Storage & Filesystem  

### Scenario  
An internal web service allows privileged users to upload a custom XML configuration file that defines a SQL query and an optional post‑processing shell command. The service stores the uploaded file in a dedicated `configs/` directory, parses the XML to extract the query and command, executes the query against the internal SQLite database, writes the query result to a CSV file in a `reports/` directory, and finally runs the specified shell command on that CSV file. Implement the handler so that all inputs are validated, XML external entities are disabled, database access uses safe query handling, file paths are confined to the allowed directories, and the shell command is executed without allowing injection.

### Functional Requirements  
- Accept a file upload named `config.xml` from an authenticated user.  
- Store the uploaded file under `configs/` using a sanitized filename that cannot escape this directory.  
- Parse the XML configuration securely, extracting:  
  - `<sql>` element containing a single SELECT statement.  
  - Optional `<command>` element containing a shell command to run on the generated report.  
- Execute the extracted SQL statement against the provided SQLite database using parameterized queries; do not concatenate user‑supplied values into the statement.  
- Write the query result to a CSV file named `<sanitized_config_name>.csv` inside the `reports/` directory.  
- If a `<command>` is present, execute it with the CSV file path as its sole argument, ensuring no additional command‑line injection is possible.  
- Return a JSON response indicating success and the path to the generated report, or an appropriate error message for validation failures.

### Constraints  
- Use only Python standard library modules.  
- All file operations must stay within the `configs/` and `reports/` directories; absolute paths, `..` segments, or null bytes in filenames must be rejected.  
- XML parsing must disable external entity resolution.  
- The shell command must be invoked without invoking a shell interpreter (e.g., using `subprocess.run` with a list of arguments).  
- The implementation must reside in a single Python file and not exceed 80 lines of code.