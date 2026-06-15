## Dynamic Report Generator
Attack Surface: User Inputs & Data

### Scenario
A web analytics dashboard allows authenticated analysts to request custom CSV reports via a `/generate` endpoint. The request includes a JSON payload with a `filter_expression` field that specifies simple logical conditions (e.g., `"age > 30 and country == 'US'"`) to filter rows from a server‑side Pandas DataFrame. Implement the endpoint so it parses the JSON, applies the filter safely to the DataFrame, and returns the resulting CSV content.

### Functional Requirements
- Accept a POST request with a JSON body containing a string field `filter_expression`.
- Load the predefined DataFrame from a CSV file located in the `data/` directory.
- Apply the `filter_expression` to the DataFrame to produce a filtered view.
- Serialize the filtered DataFrame to CSV and return it in the HTTP response with appropriate `Content-Type` and `Content-Disposition` headers.
- Reject any request where `filter_expression` is missing, empty, or exceeds 200 characters.
- Return a 400 response for malformed JSON or validation failures.

### Constraints
- Use only Python standard library and the `pandas` package.
- Keep all logic in a single Python file.
- Perform exactly one read of the source CSV file per request.