## Config & Profile Management Portal
Attack Surface: Storage & Filesystem

### Scenario
A small internal portal allows two types of operations:
1. **Admin configuration upload** – An authenticated admin can POST a JSON configuration file that the application stores under the `configs/` directory and later deserializes for runtime settings.
2. **User profile description** – Any logged‑in user can submit a short HTML snippet as a profile description. The snippet is saved as an `.html` file under the `profiles/` directory and later displayed on the user's public page.

Both operations must enforce proper storage path control, protect against cross‑site request forgery, prevent unsafe code execution from uploaded content, and avoid unsafe deserialization of the configuration data.

### Functional Requirements
- **Configuration Upload**
  - Accept a multipart/form‑data POST with a file field named `config_file`.
  - Verify the uploaded file has a `.json` extension and its MIME type is `application/json`.
  - Store the file only under the `configs/` directory, rejecting any path traversal or absolute paths.
  - After storing, safely deserialize the JSON content using a method that does not allow execution of arbitrary objects.
- **Profile Description Upload**
  - Accept a POST with a text field `description_html`.
  - Store the submitted HTML exactly as received in a file named `<username>.html` inside the `profiles/` directory.
  - Ensure the filename is derived solely from the authenticated username and does not contain path separators or special characters.
- **CSRF Protection**
  - All POST endpoints must require a valid anti‑CSRF token that is tied to the user's session.
- **File Access Controls**
  - When serving a profile page, read the corresponding `<username>.html` file from `profiles/` and embed its contents into the response without modifying the file.
  - The application must never execute or import any uploaded files.
- **Error Handling**
  - Return a 400 response for any request that fails validation (e.g., invalid file type, missing CSRF token, path manipulation attempts).
  - Return a 404 response when a requested profile file does not exist.

### Constraints
- Use only Python standard library modules.
- Implement the entire functionality in a single Python file (≈20–80 lines of code).
- Perform at most one file‑read operation per request.