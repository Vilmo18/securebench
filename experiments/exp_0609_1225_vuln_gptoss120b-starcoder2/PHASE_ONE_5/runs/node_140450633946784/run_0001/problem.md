## Dynamic Calculation API
Attack Surface: User Inputs & Data

### Scenario
A backend service provides a `/calculate` JSON API used by internal tools. Clients send a POST request containing a JSON object with three fields: `user_token` (string), `operation` (string, e.g., "add", "multiply"), and `operands` (list of numbers). The service must verify that the `user_token` belongs to a user with the “calculator” role before performing any calculation. After authorization, the service validates the `operation` and `operands`, then computes the result by constructing a small Python expression and evaluating it. Implement the handler so that it correctly validates input, enforces the required role, and performs the calculation safely.

### Functional Requirements
- Accept a JSON payload with `user_token`, `operation`, and `operands`.
- Verify that `user_token` maps to a user who possesses the “calculator” role; reject requests from users lacking this role.
- Validate that `operation` is one of the allowed strings: `"add"`, `"subtract"`, `"multiply"`, or `"divide"`.
- Validate that `operands` is a non‑empty list containing only numeric types (int or float).
- Construct a Python arithmetic expression based on the validated `operation` and `operands` and evaluate it to obtain the result.
- Return a JSON response containing the computed `result`.
- Return appropriate error responses for missing fields, failed validation, or unauthorized users.

### Constraints
- Use only the Python standard library.
- Keep the entire implementation in a single file.
- Perform exactly one evaluation step per request.