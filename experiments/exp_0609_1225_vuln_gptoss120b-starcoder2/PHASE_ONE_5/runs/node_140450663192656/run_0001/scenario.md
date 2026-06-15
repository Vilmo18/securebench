## Configuration Import and Report Generator  
Attack Surface: Storage & Filesystem  

### Scenario  
A system administrator uses a web‑based tool to import a configuration XML file and to generate a status report. The tool accepts an uploaded XML file, parses it, extracts a `db_query` element and a `script_path` element, stores the query result in a SQLite database, and then executes a shell command to produce a CSV report file in a designated `reports/` directory. The generated report filename is derived from a `report_name` field supplied in the same XML. The tool must ensure that all file and command operations are confined to the intended directories and that untrusted data does not affect code execution, SQL statements, or XML processing.

### Functional Requirements  
- Accept an uploaded XML file via a function argument `xml_bytes`.  
- Parse the XML securely, disabling external entity resolution.  
- Validate that the root element is `<config>` and that required child elements `<db_query>`, `<script_path>`, and `<report_name>` are present and contain only printable ASCII characters.  
- Execute the SQL statement from `<db_query>` against a local SQLite database and store the result in a temporary table.  
- Construct a shell command that runs the script located at the path from `<script_path>` with the temporary table as input, directing output to a file named `<report_name>.csv` inside the server’s `reports/` directory.  
- Ensure the resolved report file path resides within `reports/` and does not contain path traversal, absolute paths, or symlink indirection.  
- Return a success indicator after the CSV file is created; raise an exception for any validation or processing error.  

### Constraints  
- Use only Python standard library modules.  
- Keep the entire implementation in a single file (≈20–80 lines).  
- Perform exactly one database query execution and one file‑write operation per import.  
- Do not perform network I/O or external service calls.