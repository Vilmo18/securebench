## Configurable Maintenance Script Attack Surface: Execution Environment & Infrastructure
### Scenario
A system administration script called **ConfigMaintenance** is executed by a privileged user to run database queries and cleanup commands defined in an XML configuration file. The script obtains the configuration file path from the environment variable `CM_CONFIG`. The XML file contains:
- A database connection string.
- A parameterized SQL query template that includes a placeholder for a tenant identifier.
- A shell command template that includes a placeholder for the tenant identifier.
- A directory path for log output.

The user provides a single command‑line argument `tenant_id`. ConfigMaintenance must read the configuration, substitute the tenant identifier into the SQL and command templates, execute the SQL query, run the cleanup command, and write a log file in the specified directory.

### Functional Requirements
- Read the `CM_CONFIG` environment variable; terminate with an error if it is unset or empty.
- Resolve the configuration file path relative to the current working directory; reject absolute paths, parent‑directory traversal, and null‑byte sequences.
- Parse the XML configuration with a parser that disables external entity processing.
- Extract `db_connection`, `sql_template`, `cmd_template`, and `log_dir` from the XML.
- Accept a single command‑line argument `tenant_id`; validate that it contains only ASCII letters and digits.
- Execute the SQL query by using a parameterized statement with `tenant_id` as a bound parameter.
- Build the cleanup command by safely inserting the sanitized `tenant_id` into `cmd_template` and invoke it using the system shell.
- Write a log file named `maintenance_{tenant_id}.log` inside the `log_dir`; reject any log path that would escape the configured directory via traversal or symbolic link.
- Output a success message on completion; on any validation or execution error, output an error message and exit with a non‑zero status.

### Constraints
- Implement the script in a single Python file.
- Use only modules from the Python standard library.
- Perform at most one database query and one file‑write operation per execution.