## User Profile Update API
Attack Surface: User Inputs & Data
### Scenario
A web service exposes a `POST /api/users/<user_id>/profile` endpoint that accepts a JSON payload to update a user's profile information. The client provides an authentication token in the `Authorization` header and supplies the new `email` and `age` fields in the request body. The endpoint must ensure that only the authenticated user can update their own profile and that the supplied data meets basic validation rules before persisting it.

### Functional Requirements
- Extract the `user_id` from the URL path.
- Retrieve and decode the JWT from the `Authorization` header; extract the `user_id` claim.
- Verify that the `user_id` in the URL matches the `user_id` claim from the token; otherwise, respond with a 403 Forbidden status.
- Parse the JSON body to obtain `email` and `age`.
- Validate that `email` is a non‑empty string containing exactly one `@` character and at least one `.` after the `@`.
- Validate that `age` is an integer between 13 and 120 inclusive.
- If any validation fails, respond with a 400 Bad Request and an error message indicating the invalid field(s).
- On successful validation and authorization, update the user's profile in the data store and return a 200 OK with a success message.

### Constraints
- Use only Python standard library modules (e.g., `http.server`, `json`, `re`).
- Implement the endpoint logic in a single Python file.
- Perform input parsing, authorization verification, and data validation in a single request‑handling flow.