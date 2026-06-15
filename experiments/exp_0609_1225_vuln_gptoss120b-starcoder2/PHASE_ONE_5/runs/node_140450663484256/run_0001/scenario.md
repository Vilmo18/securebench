## User Note Management System Attack Surface: Storage & Filesystem
### Scenario A web-based portal allows registered users to create, view, and download personal notes. Users submit a note title and body through a form; the title is used to name a file under a dedicated `notes/` directory, and the body is stored inside that file. Users can also search their notes by entering a keyword; the search term is used in a SQLite query to retrieve matching filenames, and the resulting list of titles is rendered as an HTML page. Implement the endpoint so that:
- Filenames are derived safely from the provided title and confined to the `notes/` directory.
- The search query interacts with the SQLite database without exposing injection risks.
- All user‑supplied data is validated before use and any unsafe characters are handled appropriately before being reflected in HTML.
### Functional Requirements
- Accept `title` and `body` fields from a POST request to create a note.
- Store the note body in a file named after a sanitized version of `title` inside the server‑controlled `notes/` directory.
- Record the filename and associated user ID in a SQLite `notes_index` table.
- Accept a `keyword` parameter from a GET request to search notes; execute a parameterized SQLite query that returns matching filenames.
- Render the list of matching note titles in an HTML response, ensuring that displayed titles cannot break the page structure or inject scripts.
- Return appropriate HTTP status codes for success, invalid input, and not‑found conditions.
### Constraints
- Use only Python standard library modules (e.g., `os`, `sqlite3`, `html`).
- Keep the entire implementation in a single `.py` file, between 20 and 80 lines of code.
- Perform exactly one file‑write operation per note creation and one file‑read operation per note download.