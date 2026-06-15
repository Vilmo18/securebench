## Admin Widget Configuration Portal Attack Surface: Authentication & Access Control  

### Scenario  
An enterprise web application provides an admin‑only portal where authenticated administrators can configure custom widgets that will appear on the company dashboard. After logging in with a username and password, an admin submits a JSON payload containing several fields:

* `js_code`: JavaScript intended to run on the dashboard page.
* `sql_query`: A SELECT statement to retrieve data for the widget.
* `xml_config`: An XML document that defines widget layout and external resources.
* `serialized_data`: A Base64‑encoded pickled object that supplies widget metadata.
* `eval_expression`: A Python expression that will be evaluated to compute a numeric value displayed in the widget.

The application must process this payload, fetch the requested data, parse the configuration, deserialize the object, evaluate the expression, and finally render an HTML page that includes the JavaScript code, the query results, the parsed XML elements, and the evaluated result. Only users with the role `admin` are allowed to submit the payload; all other users must receive an access‑denied response.

### Functional Requirements  
- Accept a POST request to `/admin/configure` with JSON body containing `username`, `password`, `session_token`, and `widget_config` (the fields listed above).  
- Verify the supplied credentials against the user database; reject unknown users or incorrect passwords.  
- Confirm that the authenticated user has the role `admin`; reject requests from non‑admin users.  
- Parse the `widget_config` JSON object.  
- Execute the `sql_query` against the internal database using a parameterized query and retrieve the result set.  
- Parse the `xml_config` with an XML parser that explicitly disables DTDs and external entity resolution.  
- Deserialize `serialized_data` using a safe mechanism that accepts only the expected data type and forbids arbitrary object creation.  
- Evaluate `eval_expression` in a sandboxed environment that provides only a minimal set of safe built‑ins.  
- Render an HTML page that embeds the `js_code` safely (e.g., escaping), includes the query result, displays elements from the XML configuration, shows the deserialized metadata, and presents the evaluated numeric value.  
- If any step fails, return an informative error page without leaking internal details.  

### Constraints  
- Use only Python standard library modules.  
- The implementation must reside in a single Python file.  
- At most one database read per request.  
- No external network or file system access beyond the application’s own directory.  
- All input validation and sanitization must be performed before any operation that could be unsafe.