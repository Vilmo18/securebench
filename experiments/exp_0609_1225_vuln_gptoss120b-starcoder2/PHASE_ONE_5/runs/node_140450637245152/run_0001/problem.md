## Configurable Report Generator Attack Surface: Storage & Filesystem
### Scenario
A corporate intranet provides a “Generate Report” feature. Users can upload a CSV file containing product IDs. The uploaded file is saved under the server’s `uploads/` directory. An administrator later selects one of the uploaded files via a `filename` query parameter, and the application:
1. Reads the selected CSV file from disk.
2. Constructs a SQL query that retrieves product details from an internal SQLite database based on the IDs in the file.
3. Executes a system command that archives the generated report using the selected filename as part of the output archive name.
4. Renders a confirmation page that includes the filename entered by the administrator.

Implement the handler so that all inputs are properly validated, the filesystem is accessed safely, and downstream operations are performed securely.

### Functional Requirements
- Accept a multipart/form‑data upload named `data_file` and store it in the `uploads/` directory.
- Require that uploaded files have a `.csv` extension and contain only numeric product IDs separated by commas.
- Provide an endpoint that receives a `filename` query parameter, resolves the file only within the `uploads/` directory, and rejects any path that attempts directory traversal, absolute paths, or symbolic‑link escapes.
- Read the selected CSV file, parse the product IDs, and use them in a parameterized SQL query against the SQLite `products` table.
- Build a command line that invokes the system’s `tar` utility to create an archive named `<filename>_report.tar.gz` containing the generated report file, and execute it without passing unchecked data to the shell.
- Return an HTML page confirming the operation; the page must safely embed the `filename` value so that it cannot inject markup.

### Constraints
- Use only Python standard library modules.
- Keep the entire implementation in a single file (≈20–80 lines of code).
- Perform exactly one file‑read operation and one database query per request.
- Do not invoke the shell with unsanitized input; use appropriate subprocess interfaces.