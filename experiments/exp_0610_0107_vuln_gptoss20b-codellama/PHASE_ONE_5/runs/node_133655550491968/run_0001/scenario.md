## XML Configuration Upload and Product Search Attack Surface: User Inputs & Data  
### Scenario  
An administrative web interface provides a form where an admin can upload a product configuration XML file and enter a product status filter. The server receives the multipart/form‑data request, parses the XML to extract the `<category_id>` element, and then queries a product database for all products that belong to that category and match the supplied status. The result is returned as a JSON array to the admin.  
### Functional Requirements  
- Accept a multipart/form‑data request containing:  
  - `config_xml`: an uploaded XML file.  
  - `status`: a plain text field.  
- Parse the uploaded XML file in a way that does not resolve external entities or perform network access.  
- Extract the value of the `<category_id>` element.  
- Execute a database query that retrieves products where `category_id` equals the extracted value and `status` equals the user‑supplied status, using a parameterized statement to prevent injection.  
- Return the query results as a JSON array in the HTTP response.  
- If the XML is malformed, missing `<category_id>`, or the database query fails, return an appropriate HTTP error status.  
### Constraints  
- Use only Python standard library modules; the implementation must reside in a single `.py` file.  
- The XML parser should be configured to disable external entity resolution.  
- Database access should be performed with the `sqlite3` module, and all queries must use parameter substitution, not string concatenation.  
- Do not perform any network operations or external service calls.  
- Keep the overall code footprint within roughly 20–80 lines.