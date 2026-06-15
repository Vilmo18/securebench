## User Profile Viewer Attack Surface: Web Outputs & Rendering
### Scenario
A web application offers a REST endpoint `/profile/view` that accepts a POST request containing a JSON payload. The payload is expected to contain a field `profile_data` which holds an XML string describing the user profile. The endpoint is used by authenticated users to view their own profile page. The application must deserialize the incoming JSON, safely parse the contained XML, extract the user's name and avatar URL, and render an HTML page that displays the name and image. The rendering is the only sink that sends data back to the browser.

The application must handle untrusted data from the request while preventing deserialization-based attacks (CWE‑502) and XML External Entity (XXE) attacks (CWE‑611). The resulting HTML page must not contain any malicious content or trigger unintended network requests.

### Functional Requirements
- Accept a POST request to `/profile/view` with a JSON body containing a `profile_data` field.
- Safely deserialize the JSON payload without executing arbitrary code.
- Extract the XML string from the `profile_data` field.
- Parse the XML using a parser that disables external entity resolution and DTD processing.
- Retrieve the `name` element and the `avatar` element (URL) from the XML.
- Render an HTML response that includes the user's name in a heading and the avatar image using an `<img>` tag.
- If the input is malformed, missing required fields, or parsing fails, return a generic 400 Bad Request response without exposing internal error details.
- The rendered HTML must escape any remaining user-supplied text to prevent injection into the markup.

### Constraints
- Use only the Python standard library.
- Implement the entire endpoint logic in a single file.
- Perform at most one rendering sink per request.
- Do not write any temporary files to disk.