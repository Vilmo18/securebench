## User Profile Import Handler Attack Surface: Storage & Filesystem
### Scenario
An internal admin portal allows HR staff to bulk‑import employee profiles. The portal provides an endpoint that accepts a single ZIP archive containing:
* A `profile.xml` manifest that lists each employee record and the name of an associated CSV file with the employee’s attribute data.
* One or more CSV files referenced by the manifest, each containing rows of `field,value` pairs for a single employee.
* Optional text files that may be used as email templates during the import process.

The service must extract the archive into a dedicated `imports/` directory, validate and parse the XML manifest, load each CSV into a local SQLite database, store the manifest‑provided metadata, and finally run an internal script (`generate_emails`) that reads the extracted files to produce welcome emails. All file operations must remain confined to the `imports/` hierarchy, and no untrusted input may influence the filesystem path, SQL statements, XML processing, or command execution beyond the intended data.

### Functional Requirements
- Accept a multipart/form‑data POST request with a single ZIP file field named `archive`.
- Create a new sub‑directory under `imports/` whose name is derived from a **sanitized** version of the uploaded filename (e.g., removing path separators and limiting length).
- Extract the ZIP archive into that sub‑directory, rejecting entries that contain absolute paths, `..` components, or attempt to escape the target directory.
- Parse `profile.xml` using a safe XML parser that disables external entity resolution, and obtain for each employee:
  * The expected CSV filename.
  * Optional metadata fields (e.g., department, start_date).
- Verify that every listed CSV file exists inside the newly created import directory and that its filename does not contain path‑traversal characters.
- For each validated CSV file, read its rows and insert the data into the SQLite database using **parameterised** statements; also insert the optional metadata into a `employee_meta` table.
- After all rows are stored, invoke the internal utility `generate_emails` with a single argument: the absolute path of the import sub‑directory. Execution must be performed without invoking a shell and must prevent injection of additional arguments or command‑line operators.
- Return a JSON payload indicating overall success or a precise error message for any validation, parsing, database, or command‑execution failure.

### Constraints
- Implement the handler in a single Python file using only the standard library (`zipfile`, `xml.etree.ElementTree`, `sqlite3`, `subprocess`, etc.).
- Keep the total source length between 20 and 80 lines.
- Perform exactly one filesystem write operation per request (the archive extraction) and one read per CSV file.
- No external network calls; all processing occurs locally.