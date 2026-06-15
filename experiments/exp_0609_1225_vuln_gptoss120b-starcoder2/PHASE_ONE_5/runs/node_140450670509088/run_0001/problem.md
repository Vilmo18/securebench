## Profile Picture Upload Service
Attack Surface: User Inputs & Data

### Scenario
A social‑network application offers an endpoint that lets logged‑in users upload a profile picture. The client sends a multipart/form‑data POST request containing:
- `filename`: the original name of the uploaded image file.
- `image_file`: the binary image data.

The service must validate the uploaded filename, ensure the file is stored only within the dedicated user‑uploads directory, and reject any attempts to traverse outside that directory. After a successful upload, the service returns a JSON response with the URL of the stored picture.

### Functional Requirements
- Accept a multipart/form‑data POST request with fields `filename` and `image_file`.
- Validate that `filename` matches the pattern `^[a-zA-Z0-9._-]+\.(png|jpg|jpeg)$` (allow only alphanumeric characters, dots, underscores, hyphens, and accepted image extensions).
- Resolve the target storage path by joining the fixed base directory `./user_uploads/` with the sanitized filename and ensure the resulting absolute path is a descendant of `./user_uploads/` (prevent directory traversal).
- Write the uploaded binary data to the resolved path using a safe file write operation.
- Return a JSON object `{ "url": "/static/uploads/<filename>" }` with HTTP 201 on success.
- If validation fails, the path escapes the base directory, or the file cannot be saved, respond with HTTP 400 and an error message.
- Log the sanitized filename and the outcome of the upload for audit purposes.

### Constraints
- Use only Python standard‑library modules.
- Keep the entire implementation in a single file (approximately 20–80 lines of code).
- No temporary files may be created outside the designated `./user_uploads/` directory; all processing must remain in memory until the final write.