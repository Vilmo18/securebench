## Secure Product Search with User Preferences
Attack Surface: Web Outputs & Rendering

### Scenario
A web application hosts a product search page that accepts three inputs from a browser:
1. A `query` query parameter containing the user’s search terms.
2. A `prefs` multipart/form-data upload that contains an XML document describing how the search results should be displayed (e.g., grid vs. list).
3. A `settings` cookie that stores a base64‑encoded, signed pickle of a dictionary with additional UI preferences such as theme colors.

When a request is received, the application must:
- Validate the `query` string to allow only letters, digits, and spaces.
- Verify the HMAC signature of the `settings` cookie before base64 decoding and deserializing the pickle payload.
- Parse the `prefs` XML with external entity resolution disabled, rejecting any XML containing DTDs or external entities.
- Query a local SQLite database for products whose names or descriptions match the validated `query` term using a parameterized SQL statement.
- Render an HTML page that displays the retrieved products according to the combined preferences from the pickle, the XML, and defaults.
- Return the page to the browser; any errors should be shown as concise, user‑friendly messages that do not expose internal details.

### Functional Requirements
- Accept a `query` query string, a `prefs` XML upload, and a `settings` cookie.
- Verify the HMAC signature of `settings`; if invalid, discard the cookie and use default UI settings.
- Decode the base64 payload of `settings`, then safely deserialize the pickle object; if deserialization fails, fall back to defaults.
- Parse `prefs` XML with external entity processing disabled; reject any XML containing DTDs or external entities.
- Sanitize `query` to permit only alphanumeric characters and spaces; reject or escape any other characters before using it in the SQL query.
- Perform the product search against a SQLite database using a parameterized query to prevent SQL injection.
- Generate an HTML page by escaping all dynamic content (product names, descriptions, etc.) before inserting it into the template.
- If any input fails validation or parsing, display a concise, generic error message in the rendered page without revealing stack traces or internal state.

### Constraints
- Use only Python’s standard library modules (e.g., `http.server`, `sqlite3`, `pickle`, `hmac`, `hashlib`, `base64`, `xml.etree.ElementTree`).
- Keep the entire implementation in a single `.py` file.
- The application must not create, read, or write any external files except for the SQLite database file, which may reside in the same directory.
- The response must be a single HTTP entity containing the rendered HTML; no redirects or external service calls are allowed.