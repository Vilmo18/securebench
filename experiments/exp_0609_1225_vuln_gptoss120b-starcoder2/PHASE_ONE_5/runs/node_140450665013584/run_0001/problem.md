## User Profile Image Upload
Attack Surface: Storage & Filesystem

### Scenario
A web service allows registered users to upload a profile picture through a form. The uploaded file is received as binary data together with a filename supplied by the client. The application must store the image in a dedicated directory on the server (`user_images/`) and later serve it when the user’s profile page is requested. Implement the upload handler so that it validates the incoming filename, constructs a safe path under `user_images/`, and writes the file to disk. The handler should reject any request that would cause the file to be written outside the intended directory or that does not meet the accepted image type constraints.

### Functional Requirements
- Accept a multipart/form-data POST request containing a file field named `avatar` and a text field `username`.
- Verify that `username` consists only of alphanumeric characters and underscores.
- Allow only files with extensions `.png`, `.jpg`, or `.jpeg` (case‑insensitive) and reject others.
- Sanitize the supplied filename to prevent directory traversal, absolute paths, or null byte injection.
- Construct the storage path as `user_images/<username>_<sanitized_filename>`.
- If the resulting path is not located within the `user_images/` directory, reject the upload.
- Write the file contents to the constructed path with appropriate file permissions (readable by the application, not executable).
- Return a success response for valid uploads and an error response for any validation failure.

### Constraints
- Use only Python’s standard library.
- Keep the entire implementation in a single file.
- Perform exactly one file‑write operation per successful upload.