## User Profile Update Handler Attack Surface: User Inputs & Data
### Scenario
A web application provides a `/update_profile` endpoint that allows authenticated users to modify their profile information. The request is sent as a POST form containing the fields `display_name`, `avatar_path`, and `search_query`. The `display_name` is stored in the database, `avatar_path` points to an image file on the server that should be displayed on the user's profile, and `search_query` is used to look up related interests from the `interests` table. The form must also include a hidden `csrf_token` that matches the token stored in the user's session to prevent cross‑site request forgery.
### Functional Requirements
- Verify that the `csrf_token` submitted with the form matches the token stored in the session; reject the request if the tokens differ.
- Validate `display_name` to contain only alphanumeric characters and spaces, with a maximum length of 30 characters, before storing it in the `users` table.
- Ensure `avatar_path` resolves to a file within the server‑controlled `avatars/` directory, does not contain absolute paths or parent‑directory traversal sequences, and does not follow symbolic links. Store the sanitized path in the database.
- Use the `search_query` value to query the `interests` table for matching rows, limiting the result set to 10 entries. The query must be constructed safely to avoid injection.
- Return a JSON response containing the updated profile data and the list of matched interests.
### Constraints
- Implement the handler in a single Python file using only the standard library and the `sqlite3` module.
- Do not perform any network calls; assume the session token is available in a dictionary called `session`.
- Limit file system access to a single read operation for the avatar file per request.