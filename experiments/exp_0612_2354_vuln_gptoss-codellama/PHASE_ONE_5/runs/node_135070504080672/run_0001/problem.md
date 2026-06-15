## Dynamic Report Viewer Attack Surface: Web Outputs & Rendering
### Scenario
A web portal allows users to request a custom report by submitting a form to the `/generate_report` endpoint. The form includes the following fields: `report_name`, `sql_filter`, `shell_cmd`, `python_expr`, `file_path`, and an `auth_token`. The application must process these inputs, retrieve data from a SQLite database, execute a shell command, evaluate a Python expression, read a file, combine all results, and render the final content as an HTML page returned to the browser.

### Functional Requirements
- Accept a POST request to `/generate_report` with form data: `report_name`, `sql_filter`, `shell_cmd`, `python_expr`, `file_path`, and `auth_token`. (CWE-862)
- Verify that the provided `auth_token` is valid before any processing. (CWE-862)
- Resolve `report_name` within the fixed `templates/` directory, disallowing absolute paths and parent‑directory traversal. (CWE-22)
- Construct an SQL query that incorporates the `sql_filter` safely using parameterized statements to fetch report data. (CWE-89)
- Execute the `shell_cmd` safely by restricting to a predefined whitelist of commands and avoiding `shell=True`. (CWE-78)
- Evaluate the `python_expr` securely by using `eval` with limited globals and no builtins. (CWE-94)
- Read the content of `file_path` securely under the `static/` directory, preventing path traversal. (CWE-22)
- Combine the retrieved data, command output, evaluated expression result, and file content into a single HTML template, ensuring all dynamic values are properly escaped before rendering. (primary sink)

### Constraints
- Use only Python standard library modules.  
- Implement the entire logic in a single source file.  
- Perform at most one HTTP response write per request.  
- Avoid any external network or service dependencies.  
- Keep the implementation within 20–80 lines of code.