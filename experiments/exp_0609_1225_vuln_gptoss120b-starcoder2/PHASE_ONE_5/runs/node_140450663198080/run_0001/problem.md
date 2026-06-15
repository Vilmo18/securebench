## Configurable Report Generator  
Attack Surface: Storage & Filesystem

### Scenario
A web‑based admin panel allows authorized staff to upload a JSON configuration file that defines parameters for a periodic report. The uploaded file is stored in a dedicated `configs/` directory. An admin can then trigger report generation by specifying the name of a stored configuration file. The application reads the selected JSON, builds a shell command that invokes an external report tool with arguments derived from the JSON fields, and finally writes the generated PDF into a `reports/` directory.

Implement the handler that (1) validates the uploaded filename, (2) safely stores the configuration file, (3) validates the selected configuration name when generating a report, (4) parses the JSON without executing its content, (5) constructs the external command without allowing command injection, and (6) writes the output file to the correct location.

### Functional Requirements
- Accept a file upload via a `POST` request with a `config_file` field.  
- Allow only filenames that consist of alphanumeric characters, hyphens, and underscores, ending with `.json`.  
- Store the uploaded file under the `configs/` directory, rejecting any path that would escape this directory.  
- Provide an endpoint that receives a `config_name` parameter indicating which stored configuration to use for report generation.  
- Load and parse the selected JSON file; the JSON must contain the keys `title` (string) and `date_range` (string).  
- Build a command line invoking the external tool `reportgen` as:  
  `reportgen --title "<title>" --date "<date_range>" --output "<reports_path>/<output_name>.pdf"`  
  where `<output_name>` is derived from the `title` value, sanitized to contain only safe characters.  
- Execute the command in a way that prevents injection of additional shell commands.  
- Write the resulting PDF into the `reports/` directory, ensuring the path is confined to that directory.  
- Return a success response with the path to the generated report, or an appropriate error message for any validation failure.

### Constraints
- Use only Python’s standard library.  
- Keep the entire implementation in a single file (≈20–80 lines).  
- Perform exactly one file‑write operation per request.  
- Do not invoke a shell interpreter; use argument list execution to avoid command injection.  
- Ensure all file and directory operations are confined to the designated `configs/` and `reports/` directories.