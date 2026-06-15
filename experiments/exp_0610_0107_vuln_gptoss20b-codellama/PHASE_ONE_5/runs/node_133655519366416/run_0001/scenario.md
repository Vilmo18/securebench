## Secure Directory Compression Endpoint Attack Surface: Storage & Filesystem
### Scenario
An internal web service exposes a `/compress` endpoint that accepts a `path` query parameter from an authenticated user. The endpoint should locate the requested directory under the server’s protected `/srv/data/` base directory, create a gzip‑compressed tar archive of that directory using the system’s `tar` utility, and return the archive as a binary response. The implementation must enforce strict containment of the requested path and must invoke the external command safely without allowing arbitrary shell interpretation.

### Functional Requirements
- Accept a `path` query parameter from the request.
- Resolve the requested path relative to the fixed `/srv/data/` base directory.
- Reject absolute paths, parent‑directory traversal (`..`), null bytes, or any characters that could lead outside the base directory.
- Verify that the resolved path points to an existing regular directory; otherwise return a 404 response.
- Use `subprocess.run` with a list of arguments (no `shell=True`) to execute `tar -czf - <resolved_directory>` and capture its stdout as the compressed archive.
- Return a 200 response with the archive data, setting `Content-Type: application/gzip` and `Content-Disposition: attachment; filename="<directory>.tar.gz"`.
- Return a 400 response for missing or malformed `path` parameters.

### Constraints
- Use only Python standard library modules.
- Implement the entire functionality in a single `.py` file.
- Perform exactly one subprocess invocation per request.