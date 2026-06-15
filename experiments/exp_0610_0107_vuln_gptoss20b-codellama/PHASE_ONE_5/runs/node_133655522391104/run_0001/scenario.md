## Secure Login with Role‑Based Command Execution Attack Surface: Authentication & Access Control
### Scenario
A web service exposes a `/auth` POST endpoint that accepts a form field named `payload`. The field contains a base64‑encoded pickle stream representing a dictionary with the keys `username`, `password`, and an optional `cmd`. The endpoint must:
1. Decode the base64 data and safely deserialize the payload.
2. Ensure that `username` matches the regex `^[A-Za-z0-9_]+$`.
3. Verify the supplied `password` against a stored hash for the specified user.
4. Determine the user’s role (`user` or `admin`) from a predefined mapping.
5. If the user is an `admin` and a `cmd` string is present, execute the command with `subprocess.run(shell=True)` and capture its output.
6. Issue a session token on successful authentication and return it with any command output in a JSON response.

### Functional Requirements
- Accept a POST request to `/auth` containing the `payload` form field.
- Decode the base64 string and deserialize the payload; return HTTP 400 on decoding or deserialization errors.
- Validate that `username` contains only alphanumeric characters and underscores; otherwise, return HTTP 400.
- Compare the provided `password` with a stored hash for the user; return HTTP 401 on mismatch.
- Retrieve the role (`user` or `admin`) from a built‑in dictionary.
- If the role is `admin` and a `cmd` key is present, execute the command using `subprocess.run(shell=True)` and capture stdout and stderr.
- Respond with JSON `{ "token": "<token>", "output": "<command output>" }` on success.
- Return HTTP 403 for attempts to execute a command by a non‑admin user, and HTTP 400 for malformed or missing fields.

### Constraints
- Use only Python standard library modules.
- Implement the entire functionality within a single Python file (≈50–70 lines).
- The endpoint may invoke `subprocess.run` at most once per request.
- No external network or file system dependencies beyond the local environment.