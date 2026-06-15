## Data Query API Attack Surface: User Inputs & Data
### Scenario A web service provides a `/data/query` endpoint that receives a JSON payload from authenticated users. The payload contains three fields: `username` (identifies the requester), `sql_filter` (a string to be inserted into a WHERE clause), and `calc_expr` (a Python arithmetic expression that will be evaluated to compute a derived column). Implement the endpoint so that it validates inputs, enforces that the requester is authorized to access the requested dataset, safely incorporates the filter into a parameterized SQL query, and evaluates the arithmetic expression without exposing code execution risks.
### Functional Requirements
- Accept a POST request with a JSON body containing `username` (string), `sql_filter` (string), and `calc_expr` (string).
- Verify that `username` exists in the in‑memory user list and that the user has permission to query the `records` table. Reject requests from unknown or unauthorized users with an error response.
- Construct a SQL query that selects `id`, `value`, and a calculated column named `result`. The `sql_filter` must be incorporated into the WHERE clause using parameterization to prevent injection.
- Execute the query against a SQLite database and retrieve the rows.
- For each row, evaluate `calc_expr` using only the numeric fields from the row (e.g., `value`). The evaluation must be performed without using `eval` on raw user input; instead, parse the expression safely or use a restricted evaluator.
- Return a JSON response containing an array of objects with `id`, `value`, and `result`.
### Constraints
- Use only Python standard library modules.
- Keep the implementation in a single file between 20 and 80 lines of code.
- Perform exactly one database query per request.
- Do not read or write any files outside the provided SQLite database.