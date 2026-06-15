## Article Submission Handler Attack Surface: Storage & Filesystem
### Scenario
A content management system allows authenticated authors to submit new articles. Each submission includes a `title` and `body` received via an HTTP POST request. The application must store the article body as a plain‑text file on the server's `articles/` directory, using a filename derived from the title. Additionally, the title and the file path are recorded in a SQLite database to support listing and searching of articles. Implement the handler so that the filesystem interactions are safely confined to the `articles/` directory and the database interactions are protected against injection. The stored article may later be rendered in a web page, so the content must be treated to prevent script injection when displayed.

### Functional Requirements
- Accept `title` and `body` parameters from the POST request.
- Create a safe filename from the `title` (e.g., lower‑case, alphanumeric, hyphens) and ensure the resulting path resolves inside the configured `articles/` directory.
- Reject titles that would produce absolute paths, parent‑directory components, or any characters that could break the path resolution.
- Write the `body` to a file with the derived filename under `articles/`, using UTF‑8 encoding.
- Insert a new record into a SQLite database table `articles` with columns `id`, `title`, `filepath`, and `created_at`.
- Use parameterized queries for all database operations to avoid injection.
- Ensure that when the article is later displayed, the `title` and `body` are escaped or sanitized to prevent execution of injected scripts.

### Constraints
- Use only Python 3 standard library modules (e.g., `os`, ` pathlib`, `sqlite3`, `html`).
- Keep the entire implementation in a single file with no external dependencies.
- Perform exactly one file‑write operation and one database‑insert per request.