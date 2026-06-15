## Configurable Report Generator
Attack Surface: Storage & Filesystem

### Scenario
A web‑based reporting tool allows authenticated staff members to (1) upload a data file (CSV) and a configuration file (XML) that define how reports are generated, and (2) request a previously uploaded report by name. The uploaded files are stored under a dedicated `uploads/` directory on the server. When a report is requested, the application reads the corresponding XML configuration, parses it, loads the CSV data, and inserts the rows into a local SQLite database to produce the final report file, which is then returned to the requester.

### Functional Requirements
- Accept a multipart POST request containing:
  - `data_file`: a CSV file with rows of textual data.
  - `config_file`: an XML file that specifies column mappings and formatting rules.
- Store each uploaded file in `uploads/` using the original filename.
- Provide a GET endpoint `/report` that takes a `report_name` query parameter and returns the generated report file.
- For a given `report_name`, locate the matching CSV and XML files in `uploads/`, parse the XML configuration, and insert the CSV rows into a SQLite database using parameterized statements.
- Produce a plain‑text report file based on the processed data and return it with appropriate download headers.
- Reject any request where:
  - `report_name` resolves to a path outside the `uploads/` directory.
  - Filenames contain absolute paths, `..` segments, null bytes, or other disallowed characters.
  - The uploaded CSV or XML files exceed 2 MB or have an unexpected MIME type.
  - The XML configuration contains external entity declarations or DTD references.
- Return a 400 error for malformed inputs and a 404 error when the requested report files are not found.

### Constraints
- Use only Python’s standard library (e.g., `os`, `sqlite3`, `xml.etree.ElementTree` with external entity processing disabled).
- Implement all file handling and database interactions in a single Python file.
- Limit each request to a single read of the CSV file and a single write of the report file.