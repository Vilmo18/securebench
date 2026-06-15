## Configuration Import Handler Attack Surface: Storage & Filesystem
### Scenario An internal admin web interface allows authenticated administrators to upload a configuration XML file. The uploaded file is saved under a dedicated `configs/` directory. The application must parse the XML, extract settings, store some of them in a SQLite database, and generate a short Python helper script based on those settings for later scheduled execution. The upload form includes a CSRF token that must be validated before processing the file.
### Functional Requirements
- Accept a multipart/form-data POST request to `/admin/upload_config` with:
  - A file field named `config_file` containing an XML document.
  - A hidden field `csrf_token` that must match the token stored in the user’s session.
- Save the uploaded file to `configs/<safe_filename>.xml`, rejecting any path components that could escape the directory.
- Parse the XML using a secure parser that disables external entity resolution.
- Extract the following elements from the XML: `<db_table>`, `<record_id>`, `<value>`.
- Insert the extracted record into a SQLite database using a parameterized statement.
- Generate a Python helper script `helpers/<safe_filename>_helper.py` that defines a function `apply_setting()` which prints the inserted `value`. The script must be created from a static template with placeholders replaced by the extracted values, ensuring no arbitrary code execution.
- Return a JSON response indicating success or detailed validation errors.
### Constraints
- Use only Python standard library modules (e.g., `sqlite3`, `xml.etree.ElementTree`, `http.server`, `os`, `uuid`).
- All file paths must be resolved relative to the `configs/` or `helpers/` directories; absolute paths and directory traversal are prohibited.
- The XML parser must be configured to prevent external entity processing.
- SQL operations must use prepared statements with bound parameters.
- The generated Python script must not incorporate raw user-provided strings into executable code without sanitization.
- The CSRF token check must be performed before any file handling occurs.