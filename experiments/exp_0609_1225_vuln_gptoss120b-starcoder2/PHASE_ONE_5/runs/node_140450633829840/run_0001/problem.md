## User Profile Import Handler Attack Surface: Storage & Filesystem
### Scenario
A web application allows administrators to import user profiles in bulk by uploading an XML file through an admin console. The uploaded file is stored in a dedicated `imports/` directory on the server. A background job reads each `<user>` element from the XML, extracts the `username` and `email` fields, and inserts a new record into the `users` table. Implement the import handler and the processing routine so that file storage is correctly confined and the extracted data is safely incorporated into the database operation.
### Functional Requirements
- Accept an uploaded file via a form field named `profile_xml`.  
- Store the uploaded file under the `imports/` directory, rejecting absolute paths, parent‑directory traversal (`..`), and null bytes.  
- After successful upload, parse the stored XML file and iterate over each `<user>` element.  
- For each user, read the `username` and `email` child elements.  
- Insert the extracted values into the `users` table using a parameterized query to avoid injection issues.  
- Log a warning and skip any `<user>` entry that is missing required fields.  
- Return a success response indicating the number of users imported, or an error response if the upload or processing fails.
### Constraints
- Use only Python standard library modules (e.g., `os`, `xml.etree.ElementTree`, `sqlite3`).  
- Keep the entire implementation in a single Python file.  
- Perform exactly one file‑write operation for the upload and one database‑write operation per user record.  
- Do not invoke external services or network resources.