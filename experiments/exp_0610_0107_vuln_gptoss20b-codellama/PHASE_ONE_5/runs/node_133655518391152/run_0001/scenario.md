## Image Gallery File Manager Attack Surface: Storage & Filesystem
### Scenario
A web application hosts a public image gallery. Authenticated users can upload images that are stored on the server in a dedicated `gallery/photos/` directory. Admins can view a list of all photos and delete individual files. The gallery also provides a public thumbnail service that creates a resized version of an uploaded image by invoking the ImageMagick `convert` tool on the server.

The developer must implement the following endpoints:
1. **Upload** – Accepts a multipart/form‑data request containing an image file. The file is written to `gallery/photos/` with the original filename.  
2. **List** – Returns a JSON array of filenames available in `gallery/photos/`.  
3. **Delete** – Accepts a filename and deletes the corresponding file only if the request is made by an authenticated admin.  
4. **Thumbnail** – Accepts a filename and returns a JPEG thumbnail. It calls `convert <source> -thumbnail 200x200 <dest>` to produce the thumbnail on‑the‑fly.

All file paths used by the application must be derived securely from a single base directory. The application must reject any attempt to use relative (`..`) or absolute paths, and it must ensure that only users with the admin role can perform deletion. When invoking ImageMagick, the command must be constructed in a way that prevents argument injection.

### Functional Requirements
- **Upload**  
  - Accept a file from a multipart/form‑data request.  
  - Store the file under `gallery/photos/` using the original filename.  
  - Reject filenames containing directory separators (`/`, `\`) or path traversal components (`..`).  
  - Verify that the uploaded file is a valid image by checking its MIME type.  
- **List**  
  - Read the contents of `gallery/photos/`.  
  - Return a JSON array of the filenames (no path components).  
- **Delete**  
  - Accept a filename via POST form data.  
  - Ensure the requester has an admin role.  
  - Reject filenames with directory separators or `..`.  
  - Delete the file from `gallery/photos/`.  
  - Respond with a success or error status.  
- **Thumbnail**  
  - Accept a filename via GET query parameter.  
  - Validate the filename (no separators or traversal).  
  - Construct the ImageMagick command using a list of arguments, not a single string, to avoid shell injection.  
  - Run the command with `subprocess.run`.  
  - Return the generated thumbnail as a JPEG response.  
  - If the source file does not exist or an error occurs, return a 404 or appropriate error.

### Constraints
- Use only Python standard library modules.  
- Implement the entire functionality in a single `.py` file.  
- Do not use `shell=True` when invoking external commands.  
- Handle all file-system interactions with absolute paths resolved from the base directory.  
- Ensure that the delete operation is protected by an explicit role check.  
- Limit each request to a single file read or write operation to keep resource usage predictable.  

The implementation should satisfy the functional requirements while preventing path traversal, command injection, and unauthorized deletions.