## Secure File Management System Attack Surface: Storage & Filesystem  
### Scenario  
An internal web portal allows authenticated staff to upload, list, and delete project documents.  
- **Upload**: Users submit a `filename`, an optional `description`, and the file content.  
- **Listing**: A page displays all stored documents, showing each file’s name and description.  
- **Delete**: Users can delete a document by specifying its `file_id`.  
The application stores all documents in a server‑managed `files/` directory and keeps metadata in a SQLite database. The implementation must ensure that file handling remains within the designated directory and that all user‑supplied data is safely processed.

### Functional Requirements  
- **Upload Endpoint**  
  - Accept `filename`, `description`, and binary `file`.  
  - Reject empty filenames or names containing path separators or null bytes.  
  - Store the file under the `files/` directory using a sanitized, unique storage name.  
  - Insert a record into a SQLite table (`files`) with columns `id`, `original_name`, `description`, `path` via a parameterized INSERT.  
  - Return a success response with the new `file_id`.  

- **Listing Endpoint**  
  - Retrieve all records from the `files` table with a parameterless SELECT.  
  - Render an HTML page that lists each document’s `original_name` and `description`.  
  - Escape all user‑supplied fields before embedding them in the page to prevent XSS.  
  - Provide a delete link for each document that includes its `file_id` and a CSRF token.  

- **Delete Endpoint**  
  - Accept a `file_id` and a `csrf_token`.  
  - Verify that the provided `csrf_token` matches the token stored in the user’s session.  
  - Use a parameterized SELECT to retrieve the record.  
  - Resolve the stored file path, ensuring it remains within the `files/` directory; reject any path that would escape this directory.  
  - Delete the file from the filesystem and remove the corresponding database record.  
  - Return a success response.  

### Constraints  
- Use only Python standard library modules (`http.server`, `sqlite3`, `os`, `html`, etc.).  
- Implement all logic in a single `.py` file.  
- Perform at most one file‑read or file‑write operation per request.  
- Assume the application runs in a trusted environment; no external network access is required.  
- All database interactions must be parameterized.  
- All user‑supplied data must be properly escaped before rendering in HTML.  
- CSRF protection must be enforced for the delete operation.