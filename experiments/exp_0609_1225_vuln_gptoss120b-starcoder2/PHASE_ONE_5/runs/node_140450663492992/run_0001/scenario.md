## File Upload & Catalog Service
Attack Surface: Storage & Filesystem
### Scenario
A web‑based content management tool allows authenticated editors to upload resource files (images, PDFs) and to list available resources. The upload endpoint receives a `filename` and the file content. The filename is stored in a SQLite database table `resources(id INTEGER PRIMARY KEY, name TEXT, path TEXT)`. A separate endpoint renders an HTML catalog page that reads all rows from `resources` and generates `<a href="/files/<name>">...</a>` links for each entry. Implement both endpoints so that uploaded files are saved under a dedicated `uploads/` directory, the database is updated safely, and the catalog page displays the links correctly. All inputs originate from the editor and must be validated before any filesystem or database operation.
### Functional Requirements
- Accept a multipart/form‑data POST request with fields `filename` (string) and `file` (binary) for the upload endpoint.
- Validate `filename` to contain only alphanumeric characters, hyphens, underscores, and a single allowed extension (`.png`, `.jpg`, `.pdf`). Reject any other characters or patterns.
- Resolve the storage path by joining the validated `filename` to the fixed `uploads/` directory. Prevent directory traversal or absolute path usage.
- Save the uploaded file to the resolved path, overwriting any existing file with the same name.
- Insert a new record into the `resources` table using a parameterized query, storing the original `filename` and the relative path (`uploads/<filename>`).
- Implement a catalog endpoint that queries all rows from `resources` using a parameterized SELECT statement and generates an HTML page with a list of links: `<a href="/files/{{name}}">{{name}}</a>`.
- Ensure that the generated HTML safely escapes the `name` values before insertion into the page markup.
- Return appropriate HTTP status codes: `201 Created` for successful uploads, `400 Bad Request` for validation failures, and `500 Internal Server Error` for unexpected errors.
### Constraints
- Use only Python 3 standard library modules (e.g., `http.server`, `sqlite3`, `html`, `urllib.parse`, `os`).
- Keep the entire implementation in a single file not exceeding 80 lines of code.
- Perform at most one filesystem write per upload request and one database write per upload request.
- The catalog page must be rendered without invoking external templating engines.