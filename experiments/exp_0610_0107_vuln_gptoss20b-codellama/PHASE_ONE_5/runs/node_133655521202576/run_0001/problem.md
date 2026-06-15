## Dynamic Report Generator  
Attack Surface: Web Outputs & Rendering  
### Scenario  
A corporate analytics portal offers a `/generate-report` endpoint that accepts a POST request from an authenticated analyst. The client submits a JSON body with four fields:  

- **layout** – a string that specifies the visual layout of the report.  
- **config** – an XML string defining rendering options, possibly containing an `<expr>` child to compute a value.  
- **filters** – a list of key/value pairs that form the WHERE clause of a database query.  
- **payload** – a base64‑encoded binary blob that the server must deserialize.  

The server processes the request by decoding and safely deserializing the binary blob, validating the layout string, parsing the XML without external entity resolution, evaluating the optional expression in a restricted namespace, constructing a parameterized SQL query using the filters, retrieving data from an internal SQLite database, and rendering the results into an HTML page that is returned to the browser. All user‑supplied content must be escaped before inclusion in the final HTML.

### Functional Requirements  
- Accept a POST request to `/generate-report` with a JSON body containing exactly the keys `layout`, `config`, `filters`, and `payload`. Return a 400 response for missing or extra keys.  
- Decode `payload` from base64 and deserialize it with the `pickle` module, allowing only primitive types (strings, integers, lists, dictionaries). Abort deserialization if any other object type is encountered.  
- Validate that `layout` is a non‑empty string containing only alphanumeric characters, spaces, and the allowed directives `{header, footer, table}`. Reject any string with disallowed characters or patterns.  
- Parse `config` with `xml.etree.ElementTree` while disabling external entity resolution. Ensure the parsed tree includes only the expected tags (`options`, `expr`) and attributes.  
- If an `<expr>` element is present, evaluate its text content with `eval` in a namespace that exposes only safe built‑ins (`len`, `sum`, `abs`) and no module imports. Reject any expression that attempts to access disallowed objects or modules.  
- Build a SELECT query that applies each key/value pair in `filters` as a parameterized WHERE clause, using bound parameters to prevent injection.  
- Execute the query against an internal SQLite database and fetch the resulting rows.  
- Render an HTML page that displays the retrieved data in a table. Escape all user‑supplied content (including `layout` and any data returned from the database) with a standard HTML escaping function before inserting it into the page. The rendered HTML is the sole output sink.  
- For any validation, parsing, or execution error, return a user‑friendly error page that does not expose internal stack traces or configuration details.  
- Include the header `Content-Type: text/html` in the response.

### Constraints  
- The implementation must reside in a single Python file using only the standard library.  
- The application must support Python 3.8 or newer.  
- No external network or database connections are required; an in‑memory SQLite database may be used for demonstration.  
- The implementation must perform at most one file‑read sink per request.  
- All user‑supplied data must be strictly validated and escaped before being included in the final HTML output.