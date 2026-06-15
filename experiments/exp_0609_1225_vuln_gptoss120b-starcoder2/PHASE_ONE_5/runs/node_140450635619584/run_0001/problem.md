## User Profile Import API Attack Surface: Data Exchange & External Services
### Scenario
A SaaS platform allows administrators to import user profiles from partner systems via a POST `/api/v1/import_profiles` endpoint. The request body contains a JSON array of profile objects. Each profile includes fields such as `username`, `email`, `role`, and an optional `metadata` object that may hold arbitrary key‑value pairs. The service must parse the incoming JSON, validate each profile, and store the records in the internal database. Implement the handler so that only well‑formed, allowed data is accepted and any potentially unsafe serialized content is rejected before it reaches the persistence layer.
### Functional Requirements
- Accept a POST request with a JSON payload containing an array of user profile objects.
- For each profile, verify that required fields `username`, `email`, and `role` are present and conform to expected formats (e.g., email pattern, allowed role values).
- Ensure that the optional `metadata` field, if present, is a plain JSON object with string keys and values; reject any nested objects, arrays, or non‑string values.
- Reject the entire request with a 400 response if any profile fails validation.
- Upon successful validation, convert each profile into a dictionary suitable for insertion into the database and return a 200 response with a summary of imported records.
### Constraints
- Use only Python's standard library for JSON parsing and validation.
- Keep the entire implementation within a single Python file.
- Perform validation before any deserialization into application‑specific objects or database operations.