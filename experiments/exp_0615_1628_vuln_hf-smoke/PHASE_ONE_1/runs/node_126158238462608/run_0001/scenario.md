## Secure Order Filter Endpoint Attack Surface: Web Outputs & Rendering
### Scenario
A web application exposes a `/orders/filter` endpoint that accepts a POST request containing a Base64‑encoded pickled dictionary of filter parameters (e.g., status, date range). The endpoint deserializes the data, applies the parameters to a SQL query against a SQLite database of orders, and returns an HTML page listing the matching orders. The application must securely handle the deserialization, protect against SQL injection, and render the results without leaking sensitive information.

### Functional Requirements
- Accept a `filter_payload` form field containing a Base64‑encoded pickled dictionary.
- Decode the payload from Base64.
- Perform safe deserialization, ensuring the object is a dictionary with only allowed keys (`status`, `start_date`, `end_date`).
- Use the extracted parameters in a parameterized SQL query against the `orders` table.
- Retrieve matching rows and render an HTML table displaying `order_id`, `customer_name`, `status`, and `total_amount`.
- Return a 400 response if the payload is missing, malformed, or contains disallowed keys.
- Return a 404 response if no orders match the filter.

### Constraints
- Use only Python standard library modules (`base64`, `pickle`, `sqlite3`, `html`, `cgi`).
- Implement the entire endpoint logic in a single Python file.
- Perform at most one database query per request.
- Do not write any external logs or files.