## User Account Update Handler  
Attack Surface: User Inputs & Data  

### Scenario  
A web application provides a form that allows an administrator to update a user’s profile information. The form submits a POST payload containing `user_id`, `username`, and `email`. The handler must ingest this data, validate the input format, verify that the requesting session belongs to an authenticated administrator, and then persist the changes to an internal user store.  

### Functional Requirements  
- Accept a POST request with `user_id`, `username`, and `email` fields.  
- Validate that `user_id` is a positive integer and does not contain non-numeric characters.  
- Validate that `username` contains only alphanumeric characters and underscores, and is between 3 and 30 characters long.  
- Validate that `email` conforms to a standard RFC‑5322 email pattern.  
- Verify that the current session is associated with an authenticated user who has the `admin` role before performing any update.  
- Persist the updated `username` and `email` for the specified `user_id` to the persistent user store.  
- Return a success response if the update is performed, or an appropriate error message if validation fails or authorization is not satisfied.  

### Constraints  
- Use only Python standard library modules.  
- Implement all logic in a single file.  
- The user store can be represented by an in‑memory dictionary for the purposes of this task.  
- Perform input validation and authorization checks before any data is written to the store.  
- Ensure that the handler does not expose any error details that could aid an attacker in identifying the system’s internal structure.