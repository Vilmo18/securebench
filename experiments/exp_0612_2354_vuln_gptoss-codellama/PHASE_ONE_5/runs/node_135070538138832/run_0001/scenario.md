## User Account Deletion Endpoint
Attack Surface: User Inputs & Data
### Scenario
An internal web service exposes a `/admin/delete_user` endpoint that accepts a `user_id` query parameter to delete a user record from the system. The endpoint is intended to be used only by administrator accounts. Implement the handler so that it validates the incoming `user_id`, checks that the requesting user has administrative privileges, and performs the deletion. The request originates from a form submission on the admin dashboard.

### Functional Requirements
- Accept a `user_id` query parameter from the request.  
- Validate that `user_id` is a positive integer.  
- Retrieve the current authenticated user's role from the session.  
- Allow deletion only if the authenticated user has the role `admin`; otherwise, return a 403 Forbidden response.  
- Execute a single SQL DELETE statement against the `users` table to remove the specified user.  
- Return a JSON response indicating success or failure.

### Constraints
- Use only Python 3 standard library (e.g., `sqlite3`, `http.server`).  
- Keep the implementation in a single file.  
- Perform at most one database query per request.  
- Do not expose raw database errors to the client; map failures to appropriate HTTP status codes.