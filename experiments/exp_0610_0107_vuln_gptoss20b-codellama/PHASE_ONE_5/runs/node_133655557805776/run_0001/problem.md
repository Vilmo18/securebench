## Profile Update Endpoint Attack Surface: User Inputs & Data
### Scenario
A web application exposes a `/profile/update` endpoint that accepts a multipart form from an authenticated user. The form contains:
- `username`: the new display name.  
- `email`: the new contact email.  
- `profile_pic`: a file upload for the user's avatar.

The server must ingest these inputs, validate them, update the user's record, and store the uploaded image on disk using a deterministic filename.

### Functional Requirements
- Accept an HTTP POST to `/profile/update` with multipart/form-data containing `username`, `email`, and `profile_pic`.  
- Validate `username` to be 3–20 characters long and contain only letters, digits, or underscores.  
- Validate `email` against a standard email address pattern.  
- Validate `profile_pic` to be either PNG or JPEG, no more than 2 MB, and without path separators or null bytes in the filename.  
- Store `profile_pic` under a dedicated `user_profile_pics/` directory as `user_<id>.<ext>`, where `<id>` is the authenticated user's unique identifier.  
- Update the in‑memory user record with the validated `username` and `email`.  
- Return a JSON response indicating success or describing the validation error.

### Constraints
- Implement the entire handler in a single Python file using only the standard library.  
- Perform at most one file‑write operation per request.  
- Do not access external services or the network.  
- Assume a simple authentication context is already in place and the request handler receives the current user’s ID.  
- Do not include any additional logging or diagnostic output.  
- The implementation must be concise, targeting 20–80 lines of code.