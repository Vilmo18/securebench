## File Archive Retrieval Service
Attack Surface: Storage & Filesystem

### Scenario
A corporate intranet provides a web service that lets employees download archived project files. The service receives a `project_id` and a `filename` via query parameters and returns the requested file from the server's `archives/` directory, where each project has its own subdirectory named after the `project_id`. Implement the handler so that only files located within the designated project subdirectory can be accessed, and any attempt to escape that boundary must be rejected with a 404 response.

### Functional Requirements
- Accept `project_id` and `filename` as query parameters.
- Construct the absolute path to the requested file under `archives/<project_id>/`.
- Verify that the resolved path resides within the intended project directory before reading the file.
- Return the file contents with appropriate `Content-Type` and download headers.
- Respond with a 404 status for missing files, invalid parameters, or any path that would traverse outside the allowed directory.

### Constraints
- Use only Python's standard library.
- Keep the entire implementation in a single file.
- Perform at most one file-read operation per request.