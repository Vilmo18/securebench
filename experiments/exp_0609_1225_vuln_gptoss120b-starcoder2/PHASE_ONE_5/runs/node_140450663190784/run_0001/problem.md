## Config Archive Service
Attack Surface: Storage & Filesystem

### Scenario
An internal tool allows authenticated administrators to upload JSON configuration files that will be archived on the server. The service receives a multipart/form-data request containing:
- `filename` – the desired name for the configuration file (e.g., `app_config.json`).
- `config_data` – the raw JSON content uploaded by the administrator.

The application must:
1. Verify that the requester has administrator privileges before processing the upload.
2. Deserialize the JSON content to ensure it is well‑formed.
3. Store the file under the dedicated directory `/var/app/configs/`, preventing any path‑traversal attempts.
4. After successful storage, invoke the system’s `tar` utility to create a compressed archive (`.tar.gz`) of the newly saved file, placing the archive in `/var/app/archives/`.

### Functional Requirements
- Accept a `filename` and `config_data` from the request.
- Confirm the requester’s role is *administrator*; reject the request otherwise.
- Parse `config_data` as JSON and reject the upload if parsing fails.
- Construct the target path as `/var/app/configs/<filename>` and ensure the resulting path resides within that directory (no `..` segments, no absolute paths, no symbolic‑link escapes).
- Write the validated JSON content to the target file using UTF‑8 encoding.
- Execute the command `tar -czf /var/app/archives/<filename>.tar.gz -C /var/app/configs <filename>` to create the archive, ensuring that only the intended file is included.
- Return a success response when the file is stored and archived; otherwise return an appropriate error status.

### Constraints
- Use only Python’s standard library.
- Implement the entire workflow in a single Python file (≈20–80 lines).
- Perform exactly one file‑write operation and one command‑execution operation per request.