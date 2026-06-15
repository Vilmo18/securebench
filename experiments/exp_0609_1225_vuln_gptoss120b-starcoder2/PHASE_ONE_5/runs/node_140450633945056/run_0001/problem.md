## Configurable Data Importer Attack Surface: Storage & Filesystem
### Scenario
A web‑based data management tool allows authenticated staff members to upload three types of files to the server’s `uploads/` directory:
1. An XML configuration file that defines processing rules.
2. A CSV data file that will be bulk‑inserted into a SQLite database.
3. An optional Python expression file that provides a custom transformation function for the imported rows.

The application must store each uploaded file safely, parse the XML configuration, load the CSV data into the database, and, if provided, apply the custom transformation before insertion. All file handling must stay within the designated `uploads/` directory, and untrusted content must be processed without allowing external entity resolution, SQL injection, or unsafe code generation.

### Functional Requirements
- Accept a multipart/form‑data POST request containing:
  - `config_xml` – the XML configuration file.
  - `data_csv` – the CSV data file.
  - `transform_py` – an optional plain‑text file containing a single Python expression that returns a transformed tuple for each CSV row.
- Store each uploaded file under `uploads/` using a filename derived from the original name but sanitized to prevent directory traversal or absolute paths.
- Parse `config_xml` using an XML parser that disables external entity resolution.
- Read `data_csv` line by line and construct parameterized SQL `INSERT` statements to add rows to the `records` table in the SQLite database.
- If `transform_py` is provided, evaluate the expression in a restricted namespace for each CSV row to obtain the transformed values before insertion.
- Return a JSON response indicating success, the number of rows inserted, and any warnings about skipped rows.

### Constraints
- Use only Python standard library modules.
- The implementation must be contained in a single file (≈20–80 lines of code).
- All filesystem operations must remain confined to the `uploads/` directory.
- No external network calls or services may be used.
- The SQLite database file resides in the same directory as the script and must be accessed using parameterized queries only.