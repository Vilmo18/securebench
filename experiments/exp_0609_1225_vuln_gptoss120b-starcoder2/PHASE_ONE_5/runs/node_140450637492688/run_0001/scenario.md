## User Avatar Management Attack Surface: Storage & Filesystem
### Scenario
A web application allows registered users to upload a personal avatar image which is stored on the server and later served when viewing user profiles. The upload endpoint receives a multipart form field named `avatar`. The filename supplied by the client is used to construct the storage path under a dedicated directory `avatars/`. Implement the upload handler and the avatar retrieval endpoint so that only valid image files are accepted, the storage path cannot be manipulated to escape the `avatars/` directory, and the retrieved file is served with the correct content type.

### Functional Requirements
- Accept a multipart `POST` request with a file field `avatar`.
- Validate that the uploaded file’s MIME type corresponds to a common image format (e.g., `image/png`, `image/jpeg`).
- Sanitize the original filename to contain only alphanumeric characters, hyphens, underscores, and a single dot before the extension.
- Construct the storage path by joining the sanitized filename to the server‑side `avatars/` directory, ensuring that the resulting path resolves inside that directory.
- Save the uploaded file to the resolved path.
- Implement a `GET /avatars/<username>` endpoint that reads the image file for the given username from the `avatars/` directory and returns it with the appropriate `Content-Type` header.
- Return a 400 response for any validation failure and a 404 response when an avatar file does not exist.

### Constraints
- Use only Python standard library modules.
- Keep the entire implementation in a single file (approximately 20–80 lines of code).
- Perform a single file‑write operation per upload and a single file‑read operation per retrieval.