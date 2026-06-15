## Profile Picture Upload Service
Attack Surface: User Inputs & Data

### Scenario
A web application provides an endpoint `/upload/avatar` that allows registered users to upload a profile picture. The request is a `multipart/form-data` POST containing:
- `user_id` (string) – the identifier of the uploading user.
- `image_file` (file) – the binary image data, must be a PNG or JPEG.
- `metadata_xml` (text field, optional) – an XML snippet supplied by the user that may include a `<caption>` element describing the picture.

The service must ingest the uploaded data, validate the user identifier and image format, securely parse the optional XML, and store the image alongside the extracted caption in an in‑memory dictionary keyed by `user_id`. After successful processing, it returns a JSON response confirming the upload.

### Functional Requirements
- Accept a `multipart/form-data` POST request with the fields described above.
- Verify that `user_id` is a non‑empty string and corresponds to an existing user in a predefined `users` set.
- Validate that `image_file` is present, its MIME type is `image/png` or `image/jpeg`, and its size does not exceed 2 MiB.
- If `metadata_xml` is provided, parse it using a secure XML parser that disables external entity definitions and references; extract the text of a `<caption>` element (if present) and store it with the image.
- Store the validated image bytes and optional caption in a global `avatars` dictionary: `avatars[user_id] = {"image": <bytes>, "caption": <string or None>}`.
- Return a JSON response `{ "status": "success", "user_id": "<user_id>" }`.
- Return HTTP 400 with a JSON error payload for any validation or XML parsing error.

### Constraints
- Use only Python 3 standard library modules (`cgi`, `http.server`, `xml.etree.ElementTree`, etc.).
- Keep the entire implementation in a single file between 20 and 80 lines of code.
- Perform exactly one XML parse per request when `metadata_xml` is present.
- Do not invoke subprocesses, `eval`, `exec`, or any dynamic code execution facilities.