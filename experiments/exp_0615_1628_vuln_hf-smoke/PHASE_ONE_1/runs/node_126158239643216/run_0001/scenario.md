## File Upload and Listing Service Attack Surface: Storage & Filesystem
### Scenario
A small internal web service allows registered users to upload documents. Each upload includes a title and a content file. The service stores the file on disk in a dedicated `uploads/` directory, records the filename and title in an SQLite database, and presents a file list page where each file can be downloaded. The list page displays the titles and links to the corresponding files.

### Functional Requirements
- Accept a multipart/form‑data request to `/upload` containing:
  - A `title` field (string, max 50 characters).
  - A `file` field (binary content, any MIME type).
- Validate that the uploaded file size does not exceed 5 MB.
- Generate a unique, filesystem‑safe filename for each upload, store the file under `uploads/` with that name.
- Insert a new record into the `files` table with columns `id` (auto‑increment), `title`, and `path` (the stored filename) using a parameterized SQL statement.
- Provide a `/files` endpoint that reads all records from the database and renders an HTML page listing each file’s title and a download link. The title must be displayed in the page without executing any embedded scripts.
- Provide a `/download/<int:id>` endpoint that retrieves the corresponding record, resolves the file path relative to `uploads/`, and serves the file with an appropriate `Content-Disposition` header.
- Reject any attempt to request a file via an absolute path, parent‑directory traversal, or other path escape. Respond with a 404 error for invalid or missing IDs.

### Constraints
- Use only Python standard library modules (`http.server`, `cgi`, `sqlite3`, `html`, `os`, `uuid`, etc.).
- Implement the entire server in a single `.py` file.
- Perform only one file‑read or file‑write operation per request.
- Store the SQLite database in the same directory as the server script.