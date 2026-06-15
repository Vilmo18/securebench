## Secure Media Upload and Retrieval Service  
Attack Surface: Storage & Filesystem  

### Scenario  
A lightweight media library allows authenticated editors to upload image files together with a caption. Uploaded files are stored under a dedicated `media/` directory on the server. The system records the stored filename and caption in a SQLite database. At application start, a binary configuration file (`config.pickle`) is read to determine the list of allowed file extensions. An administrator can request a web page that displays the filename and caption of a media item, and can also trigger a direct download of the file.  

### Functional Requirements  
- **Upload**  
  - Accept a multipart/form-data POST request containing a `file` and a `caption`.  
  - Unpickle `config.pickle` safely to obtain a list of permitted file extensions.  
  - Validate the uploaded file’s extension against the allowed list.  
  - Generate a unique, filesystem‑safe filename (e.g., UUID) and store the file under `media/`.  
  - Insert a new record into a SQLite table `media` with columns `id`, `filename`, and `caption` using a parameterized query.  

- **Download**  
  - Provide an endpoint `/download/<int:id>` that retrieves the record by `id` from SQLite using a parameterized query.  
  - Resolve the stored filename to an absolute path within the `media/` directory, ensuring no path traversal.  
  - Serve the file as an attachment with appropriate MIME type and headers.  

- **Report**  
  - Provide an endpoint `/report/<int:id>` that retrieves the record by `id` and renders an HTML page.  
  - Escape the `filename` and `caption` when inserting them into the HTML to prevent cross‑site scripting.  

### Constraints  
- Use only Python standard library modules.  
- The entire service must fit within a single Python file.  
- The configuration file `config.pickle` is loaded once at startup; the loaded object must be validated to be a dictionary containing a list of strings.  
- All database interactions must use parameterized statements.  
- File paths must be resolved using `os.path.join` and verified to remain inside the `media/` directory.  
- The service must not access any external network resources.  
- The implementation must perform at most one file-read sink per request (for the download) and one file-write sink per upload.