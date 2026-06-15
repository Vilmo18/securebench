## Employee Data Import API Attack Surface: Data Exchange & External Services
### Scenario A SaaS HR platform provides an `/api/import-employees` endpoint that accepts a POST request containing an XML payload with employee records. The service is called by partner systems to bulk‑load new hires. Implement the endpoint to parse the XML, validate each field, and store the records in the internal database. The implementation must ensure that only well‑formed, expected XML is processed, that all element values meet format constraints, and that deserialization does not permit unsafe object creation or external entity resolution.
### Functional Requirements
- Accept an HTTP POST with `Content-Type: application/xml` containing an `<Employees>` root element and multiple `<Employee>` child elements.
- For each `<Employee>`, extract `id` (integer), `name` (non‑empty string, max 100 characters), `email` (valid email format), and `startDate` (ISO‑8601 date).
- Validate that all required fields are present and conform to the specified formats; reject the request with a 400 response if any validation fails.
- Parse the XML using a safe parser that disables external entity expansion.
- Convert the validated data into internal Python objects and insert them into the database via a provided `save_employee(record)` function.
- Return a JSON summary indicating the number of successfully imported records and any records that failed validation.
### Constraints
- Use only Python standard library modules.
- The XML parser must be configured to prevent XML External Entity (XXE) processing.
- Do not deserialize arbitrary objects; only map XML elements to the predefined employee data structure.
- Keep the entire implementation within a single Python file and limit file I/O to logging if needed.