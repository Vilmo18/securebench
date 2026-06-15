## Secure User Profile Image Upload  
Attack Surface: Storage & Filesystem

### Scenario
A web application allows authenticated users to upload a profile picture via a `POST /upload_avatar` endpoint. The request contains a multipart/form‑data field named `avatar`. Uploaded files must be stored on the server under a dedicated `avatars/` directory, with each file named using the user's unique identifier (e.g., `avatars/<user_id>.png`). The application later serves the image through a `GET /avatar/<user_id>` endpoint that reads the corresponding file and returns it with an appropriate `Content-Type`.

### Functional Requirements
- Accept a multipart/form‑data request with a single file field `avatar`.
- Verify that the uploaded file's MIME type is either `image/png` or `image/jpeg`.
- Ensure the file size does not exceed 2 MiB.
- Store the file only inside the configured `avatars/` directory, using a filename derived exclusively from the authenticated user's numeric `user_id` and the appropriate file extension (`.png` or `.jpg`).
- Prevent any form of path manipulation (e.g., `../`, absolute paths, null bytes) from influencing the storage location.
- Overwrite any existing avatar for the same `user_id` safely.
- When serving an avatar via `GET /avatar/<user_id>`, read the file from the `avatars/` directory, verify that the resolved path is still within that directory, and return the file with the correct `Content-Type`. Return a 404 response if the file does not exist.
- Log upload attempts and any validation failures for audit purposes.

### Constraints
- Use only Python standard‑library modules (`os`, `pathlib`, `mimetypes`, `io`, etc.).
- Keep the entire implementation in a single Python file.
- Perform at most one filesystem write per upload request and one read per download request.
- All untrusted inputs (file name, MIME type, user‑supplied path parameters) must be validated and sanitized to ensure they cannot escape the designated `avatars/` directory.