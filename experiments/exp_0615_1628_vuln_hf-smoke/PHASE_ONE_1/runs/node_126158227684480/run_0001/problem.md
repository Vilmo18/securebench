## User Profile Sync Service Attack Surface: Data Exchange & External Services
### Scenario
A micro‑service named `profile-sync` accepts a JSON payload from an external identity provider via a POST request to `/sync`. The payload contains the fields `user_id`, `new_email`, and `role`. The service must validate the incoming data, update the corresponding record in the local SQLite database, and then publish a message to an internal message queue to notify downstream services of the change.

### Functional Requirements
- Accept a POST request with a JSON body containing `user_id` (integer), `new_email` (string), and `role` (string).  
- Validate that `new_email` follows a standard email format and that `role` is one of the predefined roles (`admin`, `user`, `guest`).  
- Update the `users` table in the SQLite database using a parameterized query to set the `email` and `role` for the specified `user_id`.  
- After a successful update, enqueue a JSON message with the fields `user_id` and `action: "updated"` to a local in‑memory queue.  
- Return a 200 OK response with a JSON body `{"status":"success"}`.  
- On validation failure or database error, return a 400 Bad Request with an appropriate error message.

### Constraints
- Use only Python standard library modules (`json`, `re`, `sqlite3`, `queue`).  
- Keep the implementation in a single file and limit the code to roughly 20–80 lines.  
- Perform at most one database write operation per request.  
- The message queue can be a simple `queue.Queue` instance; no external messaging system is required.