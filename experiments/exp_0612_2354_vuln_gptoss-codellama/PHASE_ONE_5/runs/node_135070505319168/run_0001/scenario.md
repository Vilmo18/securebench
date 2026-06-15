## Configuration Management Dashboard Attack Surface: Storage & Filesystem
### Scenario
An internal web application provides an administrator dashboard that allows users to upload configuration files, submit database queries, and delete existing configuration files. The uploaded files are stored on disk, processed as Python scripts, and may be serialized JSON that is later deserialized. The dashboard should enforce proper authorization, protect against SQL injection, avoid code injection through uploaded scripts, guard against CSRF on delete operations, and safely deserialize configuration data.
### Functional Requirements
- Accept a file upload via a multipart/form‑data request and store the file in the protected `config_files/` directory, ensuring the file name is sanitized and does not escape the target directory.
- Parse the uploaded file as a Python script and execute it in a sandboxed environment, rejecting any attempts to import disallowed modules or call forbidden functions.
- Provide an endpoint that accepts a user‑supplied `query` parameter and executes it against the internal SQLite database, ensuring that the query is parameterized to prevent unintended modification of the database schema.
- Allow authorized users to delete a configuration file by specifying its name; the deletion must be protected by an anti‑CSRF token that is validated on every request.
- Accept a serialized configuration object in JSON format, safely deserialize it using a whitelist of allowed types, and store the resulting configuration data in a persistent JSON file within the `config_files/` directory.
- Return appropriate HTTP status codes for success (200), unauthorized access (401), forbidden actions (403), bad request (400), and server errors (500).
- Log all file upload, query execution, and delete operations with timestamps and the acting user’s identifier.
### Constraints
- Implement the entire functionality in a single Python file using only the standard library.
- Perform at most one file‑system read or write per request.
- Do not use external services or network access. 
- The solution must handle concurrent requests reliably without data corruption.