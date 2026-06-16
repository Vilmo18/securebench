## User Role Update Endpoint
Attack Surface: User Inputs & Data
### Scenario
An internal web service exposes a `/update_role` API that allows privileged users to change the role of other user accounts. A client submits a JSON payload containing `target_user_id` and `new_role`. The request is authenticated via a session cookie, which identifies the requesting user and their current role. The service must enforce that only users with the `admin` role can invoke this operation. The goal is to implement this endpoint so that it correctly validates the requester’s authorization before performing the update.

### Functional Requirements
- Accept a POST request to `/update_role` with a JSON body containing:
  - `target_user_id` (integer)
  - `new_role` (string, one of `"user"`, `"moderator"`, `"admin"`)
- Extract the requester's identity and role from the session cookie. Assume a helper function `get_session_user()` that returns a tuple `(user_id, role)`.
- If the requester’s role is not `"admin"`, respond with HTTP status 403 and a JSON error message.
- If the requester is an admin, update the role of the user identified by `target_user_id` in an in-memory data store.
- Return HTTP status 200 with a JSON success message upon successful update.
- Return HTTP status 400 if the payload is missing required fields or contains invalid values.
- Return HTTP status 404 if `target_user_id` does not exist in the data store.

### Constraints
- Use only the Python standard library (e.g., `http.server`, `json`).
- Implement the entire service in a single `.py` file.
- Store user data in a simple in-memory dictionary; persistence is not required.
- The service should handle one request per execution; concurrent handling is not required.
- Do not read or write any external files; all data is kept in memory during execution.