## User Profile Sync API Attack Surface: Data Exchange & External Services
### Scenario
A SaaS platform provides a `/api/sync_profile` endpoint that accepts POST requests containing a JSON payload from partner services. The payload includes `user_id` (integer), `display_name` (string), and `bio` (string). The endpoint must upsert the user record into the internal PostgreSQL database and then return a JSON object confirming the operation. The `display_name` and `bio` fields may later be rendered in a web UI that displays user profiles, so they must be handled to prevent script injection when the data is later embedded in HTML pages.
### Functional Requirements
- Parse the incoming request body as JSON.
- Validate that `user_id` is a positive integer and that `display_name` and `bio` are strings with a maximum length of 150 characters.
- Use a parameterized SQL statement to insert or update the user record in the `users` table (`id`, `display_name`, `bio` columns).
- Return a JSON response containing `status: "ok"` and the stored `user_id`.
- Ensure that any characters in `display_name` and `bio` that could be interpreted as HTML markup are safely escaped before they are ever placed into HTML templates downstream.
### Constraints
- Implement the handler in a single Python file using only the standard library and the `psycopg2` package for database access.
- No external network calls other than the database connection.
- Keep the JSON parsing and database interaction to one logical flow per request.