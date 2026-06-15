## User Profile Update Handler
Attack Surface: User Inputs & Data
### Scenario
The web application provides a `/profile/update` endpoint that accepts a POST request containing:
- `name` – the user's display name
- `bio` – a free‑form text field
- `interests` – a comma‑separated list of tags
- `picture` – an optional file upload for the profile picture
- `search` – an optional query string parameter used to trigger a server‑side log‑search command

The same endpoint performs the following operations in order:
1. Validates a CSRF token present in the request headers. If the token is missing or invalid, the request is rejected with a `403` response.
2. Parses the `interests` field and stores the list in the user record.
3. Writes the `bio` and `name` values to a relational database using a parameterized query.
4. Executes a shell command that searches the application logs for the literal value of `search`. The command is constructed in a way that the value must be passed as a separate argument to avoid injection.
5. Parses an XML configuration fragment supplied by the user in the `picture` upload metadata. The parser must be configured to disallow external entity resolution.
6. Stores the uploaded picture file to a server‑side directory, ensuring that the file name is sanitized to prevent path traversal.
7. Returns an HTML page that displays the updated `bio`, the list of `interests`, and the name of the uploaded picture. All user‑supplied text must be properly escaped before rendering.

### Functional Requirements
- Reject any POST request that does not include a valid CSRF token.
- Accept up to 5 MB for the profile picture; reject larger files.
- Store the `name` and `bio` values in the database using a prepared statement or equivalent mechanism that separates data from the command.
- Invoke the log‑search command using a method that passes the `search` term as a separate argument, not by concatenating into a shell string.
- Parse user‑supplied XML in a secure mode that disallows external entity references.
- Sanitize the uploaded picture file name to contain only alphanumeric characters, hyphens, underscores, and a single period before the extension.
- Escape all user‑supplied text (`name`, `bio`, `interests`) before embedding it into the returned HTML.
- Return a `200` response with the profile page on success, or appropriate error codes (`400`, `403`, `413`, `500`) on failure.

### Constraints
- The entire implementation must reside in a single Python file.
- Only standard library modules may be used.
- No network calls or external services are allowed.
- The solution should perform at most one file‑write and one database write per request.