## Secure XML-Based Menu Renderer Attack Surface: Web Outputs & Rendering
### Scenario
A content‑management web portal allows editors to upload an XML file that defines a list of menu items to be displayed on a public page. Each `<item>` element contains a `<title>` element and a `<data>` element holding a base‑64 encoded, pickled Python dictionary with optional metadata (e.g., icon URL). The server must parse the XML, safely deserialize the pickled data, validate all input, and produce a single HTML page that lists each item’s title and accompanying metadata. Errors during parsing or deserialization should be caught and presented as user‑friendly messages without revealing internal paths or stack traces.

### Functional Requirements
- Accept a file upload via an HTTP POST endpoint (`/upload/menus`).
- Reject any uploaded file larger than 1 MiB.
- Parse the XML using a parser that has external entity resolution disabled to avoid XXE attacks.
- For each `<item>` element:
  - Extract the text content of `<title>`.  
  - Extract the text content of `<data>`, base‑64 decode it, and unpickle it into a dictionary.
  - Accept the dictionary only if it contains the keys `icon` (a string URL) and `order` (an integer).  
  - Ignore any items that do not meet the schema.
- Render a single HTML page that:
  - Lists each valid item’s title in an `<h3>` element.  
  - Includes the `icon` as an `<img>` tag if present.  
  - Orders the items by the `order` value.
- If the XML is malformed, contains disallowed entities, or a pickle fails to deserialize, return an HTML page with a brief, sanitized error message (e.g., “Invalid menu file. Please check the format.”).
- Ensure that all user‑supplied text is properly escaped in the final HTML to prevent injection.

### Constraints
- Use only Python’s standard library modules (e.g., `xml.etree.ElementTree`, `base64`, `pickle`, `cgi`, `html`).  
- Implement the entire solution in a single `.py` file.  
- Do not read from or write to the filesystem beyond temporary in‑memory buffers.  
- The sole external output is the generated HTML page (one primary sink).  
- Keep the overall response size under 2 MiB.  
- Avoid any network or database access.  
- Ensure that the code handles Unicode correctly and does not trigger encoding errors.  
- Do not expose stack traces or internal file paths in any error output.