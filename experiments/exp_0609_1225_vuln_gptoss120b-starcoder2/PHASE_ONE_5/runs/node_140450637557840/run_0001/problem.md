## Customer Dashboard Rendering Attack Surface: Web Outputs & Rendering
### Scenario
A SaaS application provides a `/dashboard` endpoint that accepts three query parameters from an authenticated user’s browser: `search` (a free‑text product search term), `profile_id` (an integer identifying a saved profile), and `xml_data` (an optional Base64‑encoded XML snippet supplied via a form). The endpoint must:
* Query the product catalog using `search` and display the matching items in an HTML table.
* Load the user’s profile settings from the database using `profile_id` and embed the profile name in the page header.
* If `xml_data` is present, decode it, parse the XML, extract a `<message>` element, and render its text inside a notification banner on the page.

All rendered content is sent back to the browser as a single HTML document.

### Functional Requirements
- Validate and sanitize the `search` parameter before it is used in the SQL query that retrieves product rows.
- Validate that `profile_id` is a positive integer before it is used in the SQL query that loads the profile record.
- Use parameterised queries or prepared statements for both database accesses.
- Escape any dynamic data inserted into the HTML output to prevent unintended markup execution.
- Decode the Base64 `xml_data`, parse the XML with external entity processing disabled, and extract only the text content of the `<message>` element.
- Render the extracted message inside a `<div class="banner">` element, ensuring that any characters that could form HTML tags are safely escaped.
- Return a well‑formed HTML page that includes:
  * A header showing the profile name.
  * A table listing the product results.
  * The optional notification banner when `xml_data` is provided.
- Respond with HTTP 400 for malformed input (e.g., non‑integer `profile_id`, invalid Base64, malformed XML) and HTTP 404 when the requested profile does not exist.

### Constraints
- Implement the handler in a single Python file using only the standard library and the `sqlite3` module for database access.
- Perform exactly one database query for the product search and one for the profile lookup per request.
- XML parsing must be done with external entities disabled (e.g., using `defusedxml` or equivalent safe configuration).
- All HTML generation must be performed with explicit escaping (e.g., via `html.escape`).