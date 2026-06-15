## Profile Page Rendering Handler
Attack Surface: Web Outputs & Rendering
### Scenario
A web application allows a registered user to upload a JSON profile configuration file that specifies the layout of personal information to display on their public profile page. The file is sent via a multipart/form‑data `config` field. The application deserializes the JSON, builds an internal representation of the profile layout, and renders it as an HTML page. Implement the handler so that the user’s configuration is safely parsed, validated, and rendered without exposing the application to unintended code execution or data corruption. The rendered page should display only the fields that the user explicitly requested and must escape any user‑supplied text before insertion into the HTML.

### Functional Requirements
- Accept a multipart/form‑data upload with a single field named `config` containing a UTF‑8 encoded JSON string.  
- Deserialize the JSON into a Python data structure.  
- Validate that the top‑level object is an array of field descriptors, each containing a `type` key with a value from a predefined set (`"text"`, `"date"`, `"email"`) and a `label` key with a non‑empty string.  
- Reject any configuration that contains keys outside the allowed set, missing required keys, or values of an unexpected type.  
- Generate an HTML fragment that displays each field with its label and a placeholder value according to the type.  
- Escape all user‑supplied strings to prevent injection into the rendered HTML.  
- Return the HTML fragment as the response body with a `Content-Type: text/html` header.  
- For any validation error, return a user‑friendly error message rendered in HTML and an appropriate HTTP status code (400 Bad Request).

### Constraints
- Use only the Python standard library (e.g., `json`, `html`).  
- Keep the implementation in a single file.  
- Perform at most one I/O operation (reading the uploaded config) per request.  
- Do not store the uploaded file on disk; process it directly from memory.  
- Do not use third‑party libraries for JSON parsing or HTML escaping.  
- The handler must be thread‑safe and stateless.