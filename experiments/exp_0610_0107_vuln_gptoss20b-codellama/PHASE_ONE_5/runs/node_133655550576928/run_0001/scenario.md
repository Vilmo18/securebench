## Secure File Upload and Metadata Listing Service
Attack Surface: Storage & Filesystem

### Scenario
A web application hosts a `/upload` endpoint that accepts a multipart/form‑data POST request containing a single file. The server must store the uploaded file inside a dedicated `uploads/` directory on the filesystem and insert a record into a SQLite database with the following columns: `id`, `filename`, `uploaded_by`, and `upload_time`.  
A separate `/files` endpoint renders an HTML page that lists all uploaded files. The page accepts an optional query parameter `q` to filter filenames. The list is displayed in a table, and each filename is shown as plain text within the page.

The implementation must:
* Ensure the file is saved under the `uploads/` directory and that the filename cannot be manipulated to escape this directory (no directory traversal or absolute paths).  
* Use a prepared statement to insert the file metadata into the database, guaranteeing that the `filename` value is treated as a data value, not executable SQL.  
* When generating the `/files` page, use a parameterized SQL query to retrieve the matching filenames where the name contains the `q` search term.  
* Render the resulting filenames in the HTML page with proper escaping so that any characters submitted via the upload form or query string do not create script injection in the browser.

### Functional Requirements
- **Upload Handling**
  - Accept a multipart/form‑data request with a file field named `file`.
  - Sanitize the original filename to remove path separators and disallow absolute paths.
  - Store the file under `uploads/<sanitized_filename>`, creating the directory if it does not exist.
  - Insert a record into the `uploads` table using a parameterized statement with the sanitized filename, the uploader’s identifier (from a cookie or header), and the current timestamp.
  - Return HTTP 201 Created on success; return 400 Bad Request if the file is missing or the name is invalid.

- **File Listing**
  - Accept an optional query parameter `q`. If provided, filter filenames using a case‑insensitive `LIKE` clause; otherwise list all records.
  - Retrieve matching records with a single parameterized SQL query.
  - Generate an HTML page containing a table with the columns: `ID`, `Filename`, `Uploader`, `Time Uploaded`.
  - Escape all dynamic content inserted into the HTML so that special characters (e.g., `<`, `>`, `"`, `&`) are safely rendered.
  - Return HTTP 200 OK with the rendered page; return 400 Bad Request if the query parameter cannot be processed.

### Constraints
- Use only Python standard library modules (`http.server`, `cgi`, `sqlite3`, `os`, `datetime`, `html`, `urllib.parse`).
- Keep the entire implementation in a single Python file (≤80 lines).
- Perform at most one file-write operation per request.
- Perform at most one database query per request.
- Do not write any temporary files outside the `uploads/` directory; no external services or network access are required.