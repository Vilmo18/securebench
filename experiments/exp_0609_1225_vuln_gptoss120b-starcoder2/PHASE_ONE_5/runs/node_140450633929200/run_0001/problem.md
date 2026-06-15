## Dynamic Report Generator Attack Surface: User Inputs & Data
### Scenario
A web-based analytics dashboard allows authenticated analysts to request custom CSV reports by submitting a JSON payload to the `/generate_report` endpoint. The payload contains a `filter_expression` string that will be evaluated to select rows from an internal dataset. Implement the endpoint so that it parses the incoming JSON, validates the `filter_expression`, applies it safely to the dataset, and returns the resulting CSV file. The `filter_expression` must be restricted to a whitelist of allowed comparison operators and field names; any malformed or disallowed content must cause the request to be rejected with an error response.
### Functional Requirements
- Accept a POST request with a JSON body containing a `filter_expression` field.
- Validate that `filter_expression` consists only of permitted field names (`date`, `category`, `value`) and operators (`==`, `!=`, `>`, `<`, `>=`, `<=`, `and`, `or`) and does not contain code injection constructs.
- Parse the validated expression and apply it to the in‑memory list of dictionaries representing the dataset.
- Generate a CSV string from the filtered rows and return it with the appropriate `text/csv` content type.
- Return a 400 error response if the input JSON is malformed or the `filter_expression` fails validation.
### Constraints
- Use only Python standard library modules.
- Keep the entire implementation in a single file (approximately 20–80 lines of code).
- Perform exactly one transformation of the dataset per request.