## User Profile Export Handler Attack Surface: User Inputs & Data
### Scenario
An internal web application provides a `/export_profile` endpoint that allows authenticated employees to export their own profile data as a CSV file. The request is a POST containing a JSON body with three fields: `employee_id` (string), `export_format` (must be `"csv"`), and `csrf_token`. The handler must verify the CSRF token, ensure the requester is authorized to export the requested employee's data, validate that `employee_id` contains only digits, query the employee record from a relational database, generate a CSV file in a temporary directory, and send the file back to the client. The file path must be constructed safely to avoid directory traversal, and no unauthorized users may retrieve other employees' profiles.

### Functional Requirements
- Accept a JSON POST payload with `employee_id`, `export_format`, and `csrf_token`.
- Verify that `csrf_token` matches the token stored in the user’s session.
- Confirm that the authenticated user’s role permits exporting the profile for the supplied `employee_id`.
- Validate that `employee_id` consists solely of numeric characters and is not empty.
- Use a parameterized query to retrieve the employee record from the database based on `employee_id`.
- Create a CSV file named `profile_<employee_id>.csv` inside a designated `exports/` directory; ensure the file path cannot be manipulated to escape this directory.
- Return the generated CSV file as a downloadable response with appropriate `Content-Type` and `Content-Disposition` headers.
- Respond with an error status if any validation, authorization, CSRF check, or database lookup fails.

### Constraints
- Implement the logic in a single Python file using only the standard library and a minimal DB driver (e.g., `sqlite3`).
- Do not perform any network calls outside the scope of handling the request.
- Limit file system interaction to a single write operation for the CSV file per request.